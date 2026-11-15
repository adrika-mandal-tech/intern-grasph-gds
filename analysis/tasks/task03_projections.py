"""Phase 3 — reproducible source-derived projections with manifests.

Run: python3 analysis/tasks/task03_projections.py
Outputs under analysis/projections/ plus analysis/reports/p3_projections_summary.md.

These projections are derived from the raw local CSVs, NOT from a verified Grasph
export, and are labeled as such. Every projection records: inputs and hashes, node
population (isolates kept), direction, multiedge/self-loop policy, weight formula,
candidate pair count estimated BEFORE materialisation, node/edge counts, the date
window, exclusions and build cost.

Dense cliques (products sharing a category or a seller) are reported as candidate
pair counts and stored as membership groups, not expanded to edges, unless they
fall under MAX_EXPLICIT_EDGES; when expanded, only the top edges by weight are kept
and the cap is recorded.
"""
import csv
import hashlib
import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT.parent / 'Olist-Kaggle-dataset'
OUT = ROOT / 'projections'
REPORTS = ROOT / 'reports'
MAX_EXPLICIT_EDGES = 3_000_000
INPUTS = ['olist_order_items_dataset.csv', 'olist_products_dataset.csv',
          'olist_sellers_dataset.csv', 'olist_customers_dataset.csv',
          'olist_orders_dataset.csv', 'product_category_name_translation.csv']


def load(name, columns):
    with (CSV_DIR / name).open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            yield {c: row[c] for c in columns}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def pair_count(sizes):
    return sum(k * (k - 1) // 2 for k in sizes if k > 1)


def project_members(members):
    edges = Counter()
    for entities in members.values():
        uniq = sorted(set(entities))
        for i in range(len(uniq)):
            a = uniq[i]
            for j in range(i + 1, len(uniq)):
                edges[(a, uniq[j])] += 1
    return edges


class Builder:
    def __init__(self, name):
        self.name = name
        self.started = time.time()

    def finish(self, *, nodes, edges, manifest):
        manifest = {
            'projection': self.name,
            'source': 'Raw local CSVs; NOT a verified Grasph graph snapshot',
            'built_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'build_seconds': round(time.time() - self.started, 1),
            'nodes': nodes, 'edges': edges, **manifest,
        }
        (OUT / f'{self.name}_manifest.json').write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        return manifest


def write_edges(name, edges, cap=MAX_EXPLICIT_EDGES):
    items = edges.most_common()
    truncated = len(items) > cap
    if truncated:
        items = items[:cap]
    with (OUT / f'{name}_edges.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['source', 'target', 'weight'])
        writer.writerows((a, b, w) for (a, b), w in items)
    return len(items), truncated


def write_nodes(name, ids, attributes=None):
    attributes = attributes or {}
    with (OUT / f'{name}_nodes.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'attribute', 'value'])
        for node_id in sorted(ids):
            attrs = attributes.get(node_id, {})
            if not attrs:
                writer.writerow([node_id, '', ''])
                continue
            for key, value in attrs.items():
                writer.writerow([node_id, key, value])


def main():
    OUT.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)

    items = list(load('olist_order_items_dataset.csv',
                      ['order_id', 'order_item_id', 'product_id', 'seller_id', 'price']))
    products = list(load('olist_products_dataset.csv',
                         ['product_id', 'product_category_name']))
    sellers = [r['seller_id'] for r in load('olist_sellers_dataset.csv', ['seller_id'])]
    customers = list(load('olist_customers_dataset.csv',
                          ['customer_id', 'customer_unique_id']))
    orders = list(load('olist_orders_dataset.csv',
                       ['order_id', 'customer_id', 'order_purchase_timestamp']))
    inputs = {name: sha256(CSV_DIR / name) for name in INPUTS}

    category_of = {p['product_id']: (p['product_category_name'] or '(missing)')
                   for p in products}
    person_of = {c['customer_id']: c['customer_unique_id'] for c in customers}
    purchase_month = {o['order_id']: (o['order_purchase_timestamp'] or '')[:7]
                      for o in orders}
    window = {'start': min(m for m in purchase_month.values() if m),
              'end': max(m for m in purchase_month.values() if m)}

    product_sellers = defaultdict(set)
    seller_products = defaultdict(set)
    seller_categories = defaultdict(set)
    category_sellers = defaultdict(set)
    category_products = defaultdict(set)
    order_sellers = defaultdict(set)
    order_products = defaultdict(set)
    units = Counter()
    price_sum = defaultdict(lambda: Decimal(0))
    for r in items:
        o, p, s = r['order_id'], r['product_id'], r['seller_id']
        product_sellers[p].add(s)
        seller_products[s].add(p)
        seller_categories[s].add(category_of[p])
        category_sellers[category_of[p]].add(s)
        category_products[category_of[p]].add(p)
        order_sellers[o].add(s)
        order_products[o].add(p)
        units[(o, p)] += 1
        price_sum[(o, p)] += Decimal(r['price'])

    order_person = {o['order_id']: person_of.get(o['customer_id']) for o in orders}
    person_orders, person_products, person_sellers = defaultdict(set), defaultdict(set), defaultdict(set)
    for o, products_set in order_products.items():
        person = order_person.get(o)
        if person:
            person_orders[person].add(o)
            person_products[person].update(products_set)
            person_sellers[person].update(order_sellers[o])

    seller_state = {r['seller_id']: r['seller_state'] for r in
                    load('olist_sellers_dataset.csv', ['seller_id', 'seller_state'])}
    customer_state = {c['customer_id']: c['customer_state'] for c in
                      load('olist_customers_dataset.csv', ['customer_id', 'customer_state'])}

    manifests = []
    specs = [
        ('seller_shared_products', product_sellers, sellers,
         '# distinct products sold by both sellers',
         'sellers with no item kept as isolates'),
        ('seller_shared_categories', category_sellers, sellers,
         '# distinct categories both sellers sell',
         "empty category recorded as '(missing)'"),
        ('seller_co_order', order_sellers, sellers,
         '# orders containing both sellers', 'none'),
        ('product_bought_together', order_products, product_sellers.keys(),
         '# orders containing both products (repeated units not counted twice)',
         'orders without items excluded'),
        ('category_shared_sellers', seller_categories, set(category_of.values()),
         '# sellers selling in both categories', "empty category kept as '(missing)'"),
    ]
    for name, members, node_ids, weight, exclusions in specs:
        b = Builder(name)
        estimated = pair_count(len(v) for v in members.values())
        edges = project_members(members)
        n_edges, cap_applied = write_edges(name, edges)
        write_nodes(name, node_ids, {})
        manifests.append(b.finish(
            nodes={'n_nodes': len(node_ids), 'isolates_kept': True},
            edges={'n_edges': n_edges, 'cap_applied': cap_applied},
            manifest={'direction': 'undirected', 'self_loops': 'excluded',
                      'multiedges': 'summed', 'weight': weight,
                      'candidate_pairs_estimated': estimated,
                      'inputs_sha256': inputs, 'date_window': window,
                      'exclusions': exclusions}))

    for name, members, weight, note in [
        ('product_same_category', category_products,
         '# products in the same category (clique)', 'category cliques can be dense'),
        ('product_same_seller', seller_products,
         '# products sold by the same seller (clique)', 'seller cliques can be dense'),
    ]:
        b = Builder(name)
        estimated = pair_count(len(v) for v in members.values())
        population = {p for v in members.values() for p in v}
        if estimated <= MAX_EXPLICIT_EDGES:
            n_edges, cap_applied = write_edges(name, project_members(members))
            storage = 'expanded_edges'
        else:
            n_edges, cap_applied, storage = 0, False, 'membership_groups_only'
            with (OUT / f'{name}_groups.csv').open('w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['group', 'member'])
                for group in sorted(members):
                    for member in sorted(members[group]):
                        writer.writerow([group, member])
        write_nodes(name, population, {p: {'category': c} for p, c in category_of.items()} if name == 'product_same_category' else {})
        manifests.append(b.finish(
            nodes={'n_nodes': len(population), 'isolates_kept': True},
            edges={'n_edges': n_edges, 'cap_applied': cap_applied, 'storage': storage},
            manifest={'direction': 'undirected', 'self_loops': 'excluded',
                      'multiedges': 'summed', 'weight': weight,
                      'candidate_pairs_estimated': estimated,
                      'explicit_edge_cap': MAX_EXPLICIT_EDGES, 'note': note,
                      'inputs_sha256': inputs, 'date_window': window,
                      'exclusions': 'self-loops excluded'}))

    b = Builder('order_product_incidence')
    with (OUT / 'order_product_incidence_edges.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['order_id', 'product_id', 'units', 'price_sum'])
        for (o, p), u in sorted(units.items()):
            writer.writerow([o, p, u, str(price_sum[(o, p)])])
    manifests.append(b.finish(
        nodes={'n_orders_with_items': len(order_products),
               'n_products': len(product_sellers)},
        edges={'n_edges': len(units)},
        manifest={'direction': 'bipartite undirected (order-product)', 'self_loops': 'n/a',
                  'multiedges': 'summed into units', 'weight': 'units and summed item price',
                  'inputs_sha256': inputs, 'date_window': window,
                  'exclusions': 'orders without items excluded'}))

    b = Builder('person_projection')
    total_people = len({c['customer_unique_id'] for c in customers})
    with (OUT / 'person_projection_nodes.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['person', 'orders', 'distinct_products', 'sellers', 'states'])
        for person in sorted(person_orders):
            writer.writerow([person, len(person_orders[person]),
                             len(person_products[person]), len(person_sellers[person]), ''])
    manifests.append(b.finish(
        nodes={'n_people_with_orders': len(person_orders), 'n_people_total': total_people},
        edges={'n_orders': sum(len(v) for v in person_orders.values())},
        manifest={'identity': 'customer_unique_id (never customer_id)',
                  'weight': 'orders per person; products/sellers are distinct membership',
                  'inputs_sha256': inputs, 'date_window': window,
                  'exclusions': 'orders without items not counted in products/sellers'}))

    summary = {'source': 'Raw local CSVs; NOT a verified Grasph graph snapshot',
               'date_window': window,
               'projections': [{'name': m['projection'], 'nodes': m['nodes'],
                                'edges': m['edges'], 'weight': m.get('weight'),
                                'candidate_pairs_estimated': m.get('candidate_pairs_estimated')}
                               for m in manifests],
               'inputs_sha256': inputs,
               'dense_policy': f'cliques expand only below {MAX_EXPLICIT_EDGES:,} edges'}
    (REPORTS / 'p3_projections.json').write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    md = ['# Phase 3 — source-derived projections', '',
          '**Derived from the raw local CSVs, NOT a verified Grasph export.**', '',
          f'Date window: {window["start"]} to {window["end"]}. Dense cliques expand only below '
          f'{MAX_EXPLICIT_EDGES:,} edges; otherwise membership groups are stored.', '',
          '| projection | nodes | edges | candidate pairs (est.) | weight |',
          '| --- | ---: | ---: | ---: | --- |']
    for m in manifests:
        node_count = m['nodes'].get('n_nodes', m['nodes'].get('n_people_with_orders', ''))
        md.append(f'| {m["projection"]} | {node_count} | {m["edges"].get("n_edges", "")} '
                  f'| {m.get("candidate_pairs_estimated", "")} | {m.get("weight", "")} |')
    md += ['', '## Limitations',
           '- Source-derived; graph retention of duplicate review/zip keys is unverified.',
           '- Candidate pair counts are exact from source membership, not graph degree.']
    (REPORTS / 'p3_projections_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')

    print(f'built {len(manifests)} projections in {OUT}', flush=True)
    for m in manifests:
        print(f'  {m["projection"]:26s} nodes={m["nodes"].get("n_nodes", m["nodes"])} '
              f'edges={m["edges"]}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
