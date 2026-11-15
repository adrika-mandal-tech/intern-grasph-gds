"""Phase 1 — extraction, cache and provenance (dependency-free).

Two extraction strategies share one cache format, manifest and gate:

  * ``strict`` (default, the offline-tested contract): one query per label and per
    relationship type, ``allow_truncated=False``; any short result raises
    ``Truncated`` and nothing is committed. Use a server started with the limits
    raised (manual TASK 11.6).

  * ``windows``: paginate a default-limits server over numeric node-id windows.
    A window whose result reaches the row cap (10,000) is halved; a window that
    returns fewer rows is complete; windows are disjoint, so nodes cannot repeat.
    Measured on the demo server: ``WHERE`` filters the full set *before* the cap
    (count of SP customers = 41,746 correct, and a SP filter returns the full
    10,000 cap), and the ``truncated`` flag is scan-based, not result-based, so it
    is ignored here. Completeness is proven at the gate by set-equality against the
    source CSVs — never by trusting the flag.

Cache: one ``<name>.jsonl.gz`` per table plus ``manifest.json`` with source
identity, row counts and SHA-256. Resume reuses a table only when its bytes still
match the manifest; otherwise it is re-pulled. A truncated or failed run leaves
``manifest.json["complete"] == false`` and may leave partial tables, which resume
overwrites.
"""
import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))
from grasph_client import Grasph, Truncated  # noqa: E402

CACHE = ROOT / "cached"
REPORTS = ROOT / "reports"
CSV_DIR = ROOT.parent / "Olist-Kaggle-dataset"
NAMESPACE = "olist"
MANIFEST = "manifest.json"
CAP = 10_000  # demo-server max-result-rows (default)
VECTOR_KEYS = {"entity_vector", "embedding", "vector"}
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

EXPECTED_NODES = {
    "Order": 99441, "Customer": 99441, "OrderItem": 112650, "Payment": 103886,
    "Review": 98410, "Product": 32951, "ProductCategory": 71, "Seller": 3095,
    "Geolocation": 19015,
}
EXPECTED_RELS = {
    "PLACED_BY": 99441, "HAS_ITEM": 112650, "ITEM_OF_PRODUCT": 112650,
    "SOLD_BY": 112650, "HAS_PAYMENT": 103886, "HAS_REVIEW": 98410,
    "IN_CATEGORY": 32328, "CUSTOMER_LOCATED_IN": 99163, "SELLER_LOCATED_IN": 3088,
}
PK_COLS = {
    "Order": ("order_id",), "Customer": ("customer_id",),
    "OrderItem": ("order_id", "order_item_id"),
    "Payment": ("order_id", "payment_sequential"),
    "Review": ("review_id",), "Product": ("product_id",),
    "ProductCategory": ("product_category_name",), "Seller": ("seller_id",),
    "Geolocation": ("geolocation_zip_code_prefix",),
}
REL_ENDPOINTS = {
    "PLACED_BY": ("Order", "Customer"),
    "HAS_ITEM": ("Order", "OrderItem"),
    "ITEM_OF_PRODUCT": ("OrderItem", "Product"),
    "SOLD_BY": ("OrderItem", "Seller"),
    "HAS_PAYMENT": ("Order", "Payment"),
    "HAS_REVIEW": ("Order", "Review"),
    "IN_CATEGORY": ("Product", "ProductCategory"),
    "CUSTOMER_LOCATED_IN": ("Customer", "Geolocation"),
    "SELLER_LOCATED_IN": ("Seller", "Geolocation"),
}


# --------------------------------------------------------------- validation
def ident(name):
    """Return a safe schema identifier or raise (guards every interpolated name)."""
    if not isinstance(name, str) or not _IDENT.match(name):
        raise ValueError(f"unsafe identifier: {name!r}")
    return name


def validate_rows(rows, expected, key="_id"):
    """Reject a table whose length differs from the manual total or that repeats a key."""
    if expected is not None and len(rows) != expected:
        raise ValueError(f"row count {len(rows)} != manual total {expected}")
    seen = set()
    for row in rows:
        value = row[key]
        if value in seen:
            raise ValueError(f"duplicate {key} {value!r}")
        seen.add(value)
    return True


# --------------------------------------------------------------- cache files
def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_jsonl(path, rows):
    tmp = path.with_name(path.name + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def _read_jsonl(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_manifest(path):
    file = Path(path) / MANIFEST
    return json.loads(file.read_text()) if file.exists() else None


def _write_manifest(path, manifest):
    (Path(path) / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True))


def _table_meta(path, name):
    file = Path(path) / f"{name}.jsonl.gz"
    return {"file": file.name, "rows": None, "sha256": _sha256(file)}


def _is_reusable(path, name, manifest):
    """True when the table file still matches the manifest hash, else raise on mismatch."""
    meta = manifest["tables"].get(name)
    if not meta:
        return False
    file = Path(path) / f"{name}.jsonl.gz"
    if not file.exists():
        return False
    if _sha256(file) != meta.get("sha256"):
        raise ValueError(f"corrupt cache file: {file.name}")
    return True


# --------------------------------------------------------------- extraction
def _extract_nodes(g, label, props, strategy):
    if strategy == "windows":
        return _extract_nodes_windows(g, label, props)
    ret = ", ".join(["id(n)"] + [f"n.{p}" for p in props])
    rows = g.query(f"MATCH (n:{label}) RETURN {ret}")["rows"]
    cols = ["_id"] + list(props)
    return [dict(zip(cols, row)) for row in rows]


def _extract_rels(g, rt, rdef, strategy):
    if strategy == "windows":
        return _extract_rels_windows(g, rt, rdef)
    query = (f"MATCH (a:{rdef['from_label']})-[r:{rt}]->(b:{rdef['to_label']}) "
             f"RETURN r")
    return [_rel_dict(row[0]) for row in g.query(query)["rows"]]


def _rel_dict(r):
    return {"id": r["id"], "from": r["from"], "to": r["to"],
            "properties": r.get("properties") or {}}


def _validate_endpoints(rows, rdef, node_ids):
    from_ids = {r["_id"] for r in node_ids.get(rdef["from_label"], [])}
    to_ids = {r["_id"] for r in node_ids.get(rdef["to_label"], [])}
    for row in rows:
        if row["from"] not in from_ids or row["to"] not in to_ids:
            raise ValueError(
                f"endpoint {row['from']}->{row['to']} not present in cached nodes")


# ------------------------------------------------ window extraction (default limits)
def _q(g, query, allow=False):
    if allow:
        try:
            return g.query(query, allow_truncated=True)
        except TypeError:  # minimal fakes accept only one argument
            return g.query(query)
    return g.query(query)


def _run(g, query):
    for attempt in (1, 2):
        try:
            return _q(g, query, allow=True)
        except RuntimeError as exc:
            if "QUERY_TIMEOUT" in str(exc) and attempt == 1:
                time.sleep(1)
                continue
            raise


def _bounds(g, label):
    """Tight [min, max] node-id range for a label.

    Do NOT use ``ORDER BY id(n) LIMIT 1``: measured on the demo server it is capped
    and returns a wrong extreme (Order "max" came back 110,014 while the true range
    extends past 300,000). ``min``/``max`` aggregates are computed over the whole set
    and were correct. Fall back to the global id space when an aggregate times out.
    """
    try:
        row = _run(g, f"MATCH (n:{label}) RETURN min(id(n)), max(id(n))")["rows"][0]
        return int(row[0]), int(row[1]) + 1
    except Exception:
        return 0, 1_000_000


def _collect(g, tag, qbuilder, lo, hi, keyfn, out, depth=0):
    query = qbuilder(lo, hi)
    started = time.time()
    try:
        reply = _run(g, query)
    except RuntimeError as exc:
        if "QUERY_TIMEOUT" in str(exc) and hi - lo > 1:
            mid = (lo + hi) // 2
            print(f"      {tag:24s} timeout [{lo},{hi}) -> split", flush=True)
            _collect(g, tag, qbuilder, lo, mid, keyfn, out, depth + 1)
            _collect(g, tag, qbuilder, mid, hi, keyfn, out, depth + 1)
            return
        raise
    rows = reply["rows"]
    # Honour the truncation flag, not the row count: measured on the demo server a
    # window with only 9,616 rows was still cut (true matches 14,601), so a short
    # window can be incomplete. Any flagged or capped window is split and retried.
    cut = bool(reply.get("truncated")) or len(rows) >= CAP
    if cut and hi - lo > 1:
        mid = (lo + hi) // 2
        _collect(g, tag, qbuilder, lo, mid, keyfn, out, depth + 1)
        _collect(g, tag, qbuilder, mid, hi, keyfn, out, depth + 1)
        return
    if cut:
        raise RuntimeError(f"{tag}: single id window [{lo},{hi}) still truncated")
    added = 0
    for row in rows:
        key = keyfn(row)
        if key not in out:
            added += 1
        out[key] = row
    print(f"      {tag:24s} [{lo},{hi})  rows={len(rows):>5} new={added:>5}  "
          f"{time.time() - started:4.1f}s  d{depth}", flush=True)


def _window_node_q(label, props, lo, hi):
    ret = ", ".join(["id(n)"] + [f"n.{p}" for p in props])
    return f"MATCH (n:{label}) WHERE id(n) >= {lo} AND id(n) < {hi} RETURN {ret}"


def _window_rel_q(rt, fl, tl, lo, hi):
    return (f"MATCH (a:{fl})-[r:{rt}]->(b:{tl}) "
            f"WHERE id(a) >= {lo} AND id(a) < {hi} RETURN r")


def _extract_nodes_windows(g, label, props):
    lo, hi = _bounds(g, label)
    out = {}
    _collect(g, f"node:{label}", lambda a, b: _window_node_q(label, props, a, b),
             lo, hi, lambda row: row[0], out)
    cols = ["_id"] + list(props)
    return [dict(zip(cols, row)) for row in out.values()]


def _extract_rels_windows(g, rt, rdef):
    fl, tl = rdef["from_label"], rdef["to_label"]
    lo, hi = _bounds(g, fl)
    out = {}
    _collect(g, f"rel:{rt}", lambda a, b: _window_rel_q(rt, fl, tl, a, b),
             lo, hi, lambda row: row[0]["id"], out)
    return [_rel_dict(row[0]) for row in out.values()]


# --------------------------------------------------------------- orchestration
def pull(g, path, namespace=NAMESPACE, strategy="strict"):
    """Extract every label and relationship type into ``path``; return the table report.

    ``strategy='strict'`` refuses truncation (raises ``Truncated``);
    ``strategy='windows'`` paginates a default-limits server. Both refuse a
    count mismatch, an orphan endpoint, a duplicate key, a corrupt table and a
    provenance change.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    source = getattr(g, "base", None)

    previous = _read_manifest(path)
    if previous is not None and previous.get("source") != source:
        raise ValueError(
            f"provenance mismatch: cache source {previous.get('source')!r} != {source!r}")

    manifest = {
        "source": source,
        "namespace": namespace,
        "complete": False,
        "tables": (previous or {}).get("tables", {}),
    }
    _write_manifest(path, manifest)

    schema = g.schema(namespace)
    node_defs = {n["label"]: n for n in schema["node_schemas"]}
    rel_defs = {r["rel_type"]: r for r in schema["rel_schemas"]}
    for label in node_defs:
        ident(label)
    for rt, rdef in rel_defs.items():
        ident(rt)
        ident(rdef["from_label"])
        ident(rdef["to_label"])

    tables, node_ids = {}, {}
    for label, ndef in node_defs.items():
        name = f"nodes_{label}"
        expected = EXPECTED_NODES.get(label)
        reused = _is_reusable(path, name, manifest)
        if reused:
            rows = _read_jsonl(path / f"{name}.jsonl.gz")
        else:
            props = [p["name"] for p in ndef.get("properties", [])
                     if p["name"] not in VECTOR_KEYS]
            if strategy == "strict":
                got = g.query(f"MATCH (n:{label}) RETURN count(n)")["rows"][0][0]
                if expected is not None and got != expected:
                    raise ValueError(
                        f"{label}: server count {got} != manual total {expected}")
            rows = _extract_nodes(g, label, props, strategy)
            validate_rows(rows, expected, "_id")
            _write_jsonl(path / f"{name}.jsonl.gz", rows)
            meta = _table_meta(path, name)
            meta["rows"] = len(rows)
            manifest["tables"][name] = meta
        node_ids[label] = rows
        tables[name] = {"reused": reused, "rows": len(rows), "file": f"{name}.jsonl.gz"}
        print(f"  == {label:16s} {len(rows):>7,} rows  reused={reused}", flush=True)

    for rt, rdef in rel_defs.items():
        name = f"rels_{rt}"
        expected = EXPECTED_RELS.get(rt)
        reused = _is_reusable(path, name, manifest)
        if reused:
            rows = _read_jsonl(path / f"{name}.jsonl.gz")
        else:
            if strategy == "strict":
                query = (f"MATCH (a:{rdef['from_label']})-[r:{rt}]->"
                         f"(b:{rdef['to_label']}) RETURN count(r)")
                got = g.query(query)["rows"][0][0]
                if expected is not None and got != expected:
                    raise ValueError(
                        f"{rt}: server count {got} != manual total {expected}")
            rows = _extract_rels(g, rt, rdef, strategy)
            validate_rows(rows, expected, "id")
            _write_jsonl(path / f"{name}.jsonl.gz", rows)
            meta = _table_meta(path, name)
            meta["rows"] = len(rows)
            manifest["tables"][name] = meta
        _validate_endpoints(rows, rdef, node_ids)
        tables[name] = {"reused": reused, "rows": len(rows), "file": f"{name}.jsonl.gz"}
        print(f"  == {rt:24s} {len(rows):>7,} rows  reused={reused}", flush=True)

    manifest["complete"] = True
    _write_manifest(path, manifest)
    return {"complete": True, "tables": tables}


# --------------------------------------------------------------- CSV gate
def _stream(name):
    handle = open(CSV_DIR / name, newline="", encoding="utf-8-sig")
    reader = csv.reader(handle)
    header = next(reader)
    return handle, header, reader


def _csv_of(name, wanted):
    """Yield dicts of only the requested columns (streamed; memory stays small)."""
    handle, header, reader = _stream(name)
    idx = {col: header.index(col) for col in wanted}
    try:
        for row in reader:
            yield {col: row[idx[col]] for col in wanted}
    finally:
        handle.close()


def norm_zip(value):
    """Return the zip prefix as a zero-padded 5-char string, or None when unusable."""
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text or text.lower() == "nan":
        return None
    try:
        number = int(text)
    except ValueError:
        return None
    if number < 0:
        return None
    return f"{number:05d}"


def _expected_from_csv():
    def rs(name, col):
        return {row[col] for row in _csv_of(name, [col])}

    orders = "olist_orders_dataset.csv"
    customers = "olist_customers_dataset.csv"
    items = "olist_order_items_dataset.csv"
    pays = "olist_order_payments_dataset.csv"
    revs = "olist_order_reviews_dataset.csv"
    prods = "olist_products_dataset.csv"
    sellers = "olist_sellers_dataset.csv"
    geo = "olist_geolocation_dataset.csv"
    trans = "product_category_name_translation.csv"

    cat_of = {r["product_id"]: r["product_category_name"]
              for r in _csv_of(prods, ["product_id", "product_category_name"])}
    cats = rs(trans, "product_category_name")
    zips = rs(geo, "geolocation_zip_code_prefix")

    nodes = {
        "Order": rs(orders, "order_id"),
        "Customer": rs(customers, "customer_id"),
        "OrderItem": {(r["order_id"], r["order_item_id"]) for r in _csv_of(
            items, ["order_id", "order_item_id"])},
        "Payment": {(r["order_id"], r["payment_sequential"]) for r in _csv_of(
            pays, ["order_id", "payment_sequential"])},
        "Review": rs(revs, "review_id"),
        "Product": rs(prods, "product_id"),
        "ProductCategory": cats,
        "Seller": rs(sellers, "seller_id"),
        "Geolocation": {norm_zip(z) for z in zips},
    }
    revs_rows = list(_csv_of(revs, ["review_id", "order_id"]))
    rels = {
        "PLACED_BY": {(r["order_id"], r["customer_id"]) for r in _csv_of(
            orders, ["order_id", "customer_id"])},
        "HAS_ITEM": {(r["order_id"], (r["order_id"], r["order_item_id"]))
                     for r in _csv_of(items, ["order_id", "order_item_id"])},
        "ITEM_OF_PRODUCT": {((r["order_id"], r["order_item_id"]), r["product_id"])
                            for r in _csv_of(
                                items, ["order_id", "order_item_id", "product_id"])},
        "SOLD_BY": {((r["order_id"], r["order_item_id"]), r["seller_id"])
                    for r in _csv_of(
                        items, ["order_id", "order_item_id", "seller_id"])},
        "HAS_PAYMENT": {(r["order_id"], (r["order_id"], r["payment_sequential"]))
                        for r in _csv_of(
                            pays, ["order_id", "payment_sequential"])},
        "HAS_REVIEW": {(r["order_id"], r["review_id"]) for r in revs_rows},
        "IN_CATEGORY": {(p, c) for p, c in cat_of.items() if c in cats},
        "CUSTOMER_LOCATED_IN": {(norm_zip(r["customer_zip_code_prefix"]),
                                 norm_zip(r["customer_zip_code_prefix"]))
                                for r in _csv_of(
                                    customers, ["customer_zip_code_prefix"])
                                if norm_zip(r["customer_zip_code_prefix"])
                                in {norm_zip(z) for z in zips}},
        "SELLER_LOCATED_IN": {(norm_zip(r["seller_zip_code_prefix"]),
                               norm_zip(r["seller_zip_code_prefix"]))
                              for r in _csv_of(sellers, ["seller_zip_code_prefix"])
                              if norm_zip(r["seller_zip_code_prefix"])
                              in {norm_zip(z) for z in zips}},
    }
    return nodes, rels


def _cached_node_key(rows, label):
    cols = PK_COLS[label]
    out = {}
    for row in rows:
        values = tuple(row[c] for c in cols)
        out[row["_id"]] = values[0] if len(values) == 1 else values
    return out


def gate(path):
    """Compare the cached graph to the CSV joins. Returns a list of failures."""
    path = Path(path)
    nodes_expected, rels_expected = _expected_from_csv()
    id_maps, failures = {}, []

    for label, expected in nodes_expected.items():
        rows = _read_jsonl(path / f"nodes_{label}.jsonl.gz")
        got = set(_cached_node_key(rows, label).values())
        if label == "Geolocation":
            got = {norm_zip(v) for v in got}
        ok = got == expected
        print(f"  [{'ok' if ok else 'FAIL'}] {label:16s} key set {len(got):>7,} "
              f"vs {len(expected):>7,}"
              + ("" if ok else f"  missing={len(expected - got)} "
                               f"extra={len(got - expected)}"))
        if not ok:
            failures.append(f"{label}: key set mismatch")
        id_maps[label] = _cached_node_key(rows, label)

    for rt, expected in rels_expected.items():
        rows = _read_jsonl(path / f"rels_{rt}.jsonl.gz")
        fl, tl = REL_ENDPOINTS[rt]
        got = {(id_maps[fl][r["from"]], id_maps[tl][r["to"]]) for r in rows}
        if rt in ("CUSTOMER_LOCATED_IN", "SELLER_LOCATED_IN"):
            got = {(norm_zip(a), norm_zip(b)) for a, b in got}
        ok = got == expected
        print(f"  [{'ok' if ok else 'FAIL'}] {rt:24s} pairs {len(got):>7,} "
              f"vs {len(expected):>7,}"
              + ("" if ok else f"  missing={len(expected - got)} "
                               f"extra={len(got - expected)}"))
        if not ok:
            failures.append(f"{rt}: pair set mismatch")
    return failures


# --------------------------------------------------------------- CLI
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(CACHE))
    parser.add_argument("--strategy", choices=("strict", "windows"), default="windows")
    parser.add_argument("--skip-gate", action="store_true")
    args = parser.parse_args(argv)

    REPORTS.mkdir(exist_ok=True)
    g = Grasph()
    status = g.status()
    print("status:", status, flush=True)
    want_nodes = sum(EXPECTED_NODES.values())
    want_rels = sum(EXPECTED_RELS.values())
    if status["node_count"] != want_nodes or status["relationship_count"] != want_rels:
        raise SystemExit(f"status {status['node_count']}/{status['relationship_count']} "
                         f"!= manual {want_nodes}/{want_rels}")

    started = time.time()
    report = pull(g, args.out, strategy=args.strategy)
    elapsed = time.time() - started

    failures = [] if args.skip_gate else gate(args.out)
    summary = {
        "source": g.base,
        "strategy": args.strategy,
        "seconds": round(elapsed, 1),
        "tables": report["tables"],
        "gate_failures": failures,
    }
    (REPORTS / "p1_pull_summary.json").write_text(json.dumps(summary, indent=2))
    if failures:
        print("\nGATE FAILED:")
        for line in failures:
            print("  -", line)
        return 1
    print(f"\nGATE PASSED: {want_nodes:,} nodes + {want_rels:,} relationships "
          f"cached and matched to the CSV source ({elapsed:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
