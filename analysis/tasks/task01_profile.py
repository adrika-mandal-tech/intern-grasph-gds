"""Dependency-free SOURCE CSV profiling; never claims a verified Grasph export.
Run: python3 analysis/tasks/task01_profile.py
Outputs analysis/reports/p2_{profile_summary.md,profile.json,null_rates.csv}.
Duplicate reviews are measured under first/last retention, not assumed graph policy.
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT.parent / 'Olist-Kaggle-dataset'
REPORTS = ROOT / 'reports'
SOURCES = {
    'Order': ('olist_orders_dataset.csv', 99441, ('order_id',)),
    'Customer': ('olist_customers_dataset.csv', 99441, ('customer_id',)),
    'OrderItem': ('olist_order_items_dataset.csv', 112650, ('order_id', 'order_item_id')),
    'Payment': ('olist_order_payments_dataset.csv', 103886, ('order_id', 'payment_sequential')),
    'Review': ('olist_order_reviews_dataset.csv', 99224, ('review_id',)),
    'Product': ('olist_products_dataset.csv', 32951, ('product_id',)),
    'Seller': ('olist_sellers_dataset.csv', 3095, ('seller_id',)),
    'Geolocation': ('olist_geolocation_dataset.csv', 1000163, ('geolocation_zip_code_prefix',)),
    'ProductCategory': ('product_category_name_translation.csv', 71, ('product_category_name',)),
}


def norm_zip(value):
    if value is None or str(value).strip() == '':
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number != number.to_integral_value() or not 0 <= number <= 99999:
            return None
        return str(int(number)).zfill(5)
    except Exception:
        return None


def parse_date(value):
    try:
        return datetime.fromisoformat(value) if value else None
    except (ValueError, TypeError):
        return None


def distribution(values):
    values = sorted(values)
    if not values:
        return {'n': 0}
    def q(p):
        pos = (len(values) - 1) * p
        lo = int(pos)
        return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (pos - lo)
    return {'n': len(values), 'min': values[0], 'p25': q(.25), 'median': q(.5),
            'p75': q(.75), 'p95': q(.95), 'max': values[-1], 'mean': sum(values) / len(values)}


def concentration(counts):
    vals = sorted(counts, reverse=True)
    k = max(1, math.floor(len(vals) * .01)) if vals else 0
    total = sum(vals)
    return {'entities': len(vals), 'items': total, 'top_one_percent_n_floor': k,
            'top_one_percent_items': sum(vals[:k]),
            'top_one_percent_share': sum(vals[:k]) / total if total else None,
            'degree_distribution': distribution(vals),
            'degree_histogram': dict(sorted(Counter(vals).items()))}


def main():
    REPORTS.mkdir(exist_ok=True)
    data, nulls, facts, failures, provenance = {}, [], {}, [], {}
    geo_zips = set()

    def check(name, got, expected):
        facts[name] = {'observed': got, 'expected': expected, 'passed': got == expected}
        if got != expected:
            failures.append(f'{name}: {got!r} != {expected!r}')

    for label, (filename, expected, keys) in SOURCES.items():
        path = CSV_DIR / filename
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        rows, empties, missing, seen, n = [], Counter(), Counter(), set(), 0
        with path.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames
            for row in reader:
                n += 1
                for col in cols:
                    missing[col] += row[col] is None
                    empties[col] += row[col] is not None and row[col].strip() == ''
                key = tuple(row[k] for k in keys)
                seen.add(key)
                if label == 'Geolocation':
                    geo_zips.add(norm_zip(row['geolocation_zip_code_prefix']))
                else:
                    rows.append(row)
        data[label] = rows
        provenance[label] = {'file': filename, 'sha256': h.hexdigest(), 'rows': n,
                             'unique_keys': len(seen), 'duplicate_key_rows': n - len(seen)}
        check(f'{label} source rows', n, expected)
        if label not in ('Review', 'Geolocation'):
            check(f'{label} duplicate primary keys', n - len(seen), 0)
        for col in cols:
            nulls.append({'label': label, 'property': col, 'denominator_rows': n,
                          'missing_field': missing[col], 'empty_string': empties[col],
                          'missing_or_empty_rate': (missing[col] + empties[col]) / n if n else None})
        print(f'{label}: {n:,} source rows profiled', flush=True)
    with (REPORTS / 'p2_null_rates.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(nulls[0]))
        writer.writeheader()
        writer.writerows(nulls)

    orders, customers, items = data['Order'], data['Customer'], data['OrderItem']
    products, sellers, reviews, payments = data['Product'], data['Seller'], data['Review'], data['Payment']
    ids = {label: {r[key] for r in data[label]} for label, key in
           [('Order', 'order_id'), ('Customer', 'customer_id'), ('Product', 'product_id'),
            ('Seller', 'seller_id'), ('ProductCategory', 'product_category_name')]}
    for label, prop, target in [('Order', 'customer_id', 'Customer'),
                              ('OrderItem', 'order_id', 'Order'), ('OrderItem', 'product_id', 'Product'),
                              ('OrderItem', 'seller_id', 'Seller'), ('Payment', 'order_id', 'Order'),
                              ('Review', 'order_id', 'Order')]:
        check(f'{label}.{prop} orphan rows', sum(r[prop] not in ids[target] for r in data[label]), 0)
    people = Counter(r['customer_unique_id'] for r in customers)
    check('unique people', len(people), 96096)
    check('repeat people', sum(n > 1 for n in people.values()), 2997)
    check('unique zip areas', len(geo_zips), 19015)
    for label, prop, expected in [('Customer', 'customer_zip_code_prefix', 278),
                                   ('Seller', 'seller_zip_code_prefix', 7)]:
        check(f'{label} unmatched zip rows', sum(norm_zip(r[prop]) not in geo_zips for r in data[label]), expected)
    check('products with empty category', sum(not p['product_category_name'].strip() for p in products), 610)
    check('products without category node', sum(p['product_category_name'] not in ids['ProductCategory'] for p in products), 623)
    check('orders without items', len(ids['Order'] - {r['order_id'] for r in items}), 775)
    check('orders without payments', len(ids['Order'] - {r['order_id'] for r in payments}), 1)
    check('source orders without review', len(ids['Order'] - {r['order_id'] for r in reviews}), 768)
    first, last = {}, {}
    for r in reviews:
        first.setdefault(r['review_id'], r)
        last[r['review_id']] = r
    check('unique review IDs', len(first), 98410)
    review_sensitivity = {}
    for name, values in [('source_rows', reviews), ('first_row_per_id', list(first.values())),
                         ('last_row_per_id', list(last.values()))]:
        review_sensitivity[name] = {'rows': len(values),
            'orders_without_review': len(ids['Order'] - {r['order_id'] for r in values}),
            'orders_with_multiple_reviews': sum(n > 1 for n in Counter(r['order_id'] for r in values).values()),
            'nonempty_messages': sum(bool(r['review_comment_message'].strip()) for r in values),
            'nonempty_titles': sum(bool(r['review_comment_title'].strip()) for r in values)}

    seller_counts = Counter({r['seller_id']: 0 for r in sellers})
    product_counts = Counter({r['product_id']: 0 for r in products})
    item_counts, basket_products, basket_sellers = Counter(), defaultdict(set), defaultdict(set)
    product_sellers = defaultdict(set)
    category_of = {p['product_id']: p['product_category_name'] or '(missing)' for p in products}
    category_counts = defaultdict(Counter)
    revenue, freight = Decimal(0), Decimal(0)
    seller_revenue = defaultdict(lambda: Decimal(0))
    for r in items:
        seller, product, order = r['seller_id'], r['product_id'], r['order_id']
        seller_counts[seller] += 1
        product_counts[product] += 1
        item_counts[order] += 1
        basket_products[order].add(product)
        basket_sellers[order].add(seller)
        product_sellers[product].add(seller)
        category_counts[category_of[product]][seller] += 1
        revenue += Decimal(r['price'])
        freight += Decimal(r['freight_value'])
        seller_revenue[seller] += Decimal(r['price'])
    check('orders with exactly one item', sum(n == 1 for n in item_counts.values()), 88863)
    check('multi-distinct-product orders', sum(len(v) > 1 for v in basket_products.values()), 3236)
    check('multi-seller orders', sum(len(v) > 1 for v in basket_sellers.values()), 1278)
    check('products with multiple sellers', sum(len(v) > 1 for v in product_sellers.values()), 1225)
    check('item price total BRL', str(revenue), '13591643.70')
    check('item freight total BRL', str(freight), '2251909.54')
    check('payment total BRL', str(sum((Decimal(r['payment_value']) for r in payments), Decimal(0))), '16008872.12')
    monthly, weekdays, status = Counter(), Counter(), Counter()
    delivery_days, lateness_days, malformed, negative_delivery = [], [], Counter(), 0
    for r in orders:
        dates = {}
        for col in ['order_purchase_timestamp', 'order_delivered_customer_date', 'order_estimated_delivery_date']:
            dates[col] = parse_date(r[col])
            malformed[col] += bool(r[col]) and dates[col] is None
        purchase, delivered, estimated = dates.values()
        status[r['order_status']] += 1
        if purchase:
            monthly[purchase.strftime('%Y-%m')] += 1
            weekdays[purchase.strftime('%A')] += 1
        if purchase and delivered:
            days = (delivered - purchase).total_seconds() / 86400
            delivery_days.append(days)
            negative_delivery += days < 0
        if delivered and estimated:
            lateness_days.append((delivered - estimated).total_seconds() / 86400)
    check('orders missing delivery date', sum(not r['order_delivered_customer_date'].strip() for r in orders), 2965)
    summary = {
        'source': 'Raw local CSVs; NOT a verified Grasph graph snapshot',
        'source_files': provenance, 'checks': facts, 'failures': failures,
        'people': {'denominator': len(people), 'repeat_people': sum(n > 1 for n in people.values()),
                   'repeat_share': sum(n > 1 for n in people.values()) / len(people)},
        'baskets': {'all_orders_denominator': len(orders), 'orders_with_items': len(item_counts),
                    'multi_item_orders': sum(n > 1 for n in item_counts.values()),
                    'multi_distinct_product_orders': sum(len(v) > 1 for v in basket_products.values())},
        'review_retention_sensitivity_not_graph_validation': review_sensitivity,
        'seller_item_degree': concentration(seller_counts.values()),
        'product_item_degree': concentration(product_counts.values()),
        'category_seller_concentration_active_sellers_only': {k: concentration(v.values()) for k, v in sorted(category_counts.items())},
        'temporal': {'all_months': dict(sorted(monthly.items())),
                     'analysis_months': {k: v for k, v in sorted(monthly.items()) if '2017-01' <= k <= '2018-08'},
                     'weekday_counts': dict(weekdays), 'order_status': dict(status),
                     'observed_delivery_days': distribution(delivery_days),
                     'observed_lateness_days': distribution(lateness_days),
                     'late_orders_timestamp_definition': sum(v > 0 for v in lateness_days),
                     'lateness_denominator': len(lateness_days),
                     'negative_delivery_intervals': negative_delivery, 'malformed_dates': dict(malformed)},
        'limitations': ['Nulls are CSV empty strings/missing fields, not graph property nulls.',
                       'Item degree is an incidence count, not projected seller degree.',
                       'No power-law fit or causal inference has been performed.',
                       'Duplicate-row retention is unknown until verified against graph cache.',
                       'Estimated delivery dates are midnight: timestamp lateness differs from calendar-day lateness.',
                       'Connectivity, assortativity and graph-derived profiling await projections.']}
    (REPORTS / 'p2_profile.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    md = ['# Phase 2 — source CSV profiling', '',
          '**Source-only results: NOT yet cross-checked against a live Grasph export.**', '',
          f'Checks: {len(facts)}; failures: {len(failures)}.', '', '## Integrity and manual checks']
    md += [f'- [{"x" if v["passed"] else " "}] {k}: {v["observed"]} (expected {v["expected"]})' for k, v in facts.items()]
    c = summary['seller_item_degree']
    md += ['', '## First measured findings',
           f'- Repeat people: {summary["people"]["repeat_people"]:,}/{len(people):,} ({summary["people"]["repeat_share"]:.2%}).',
           f'- Multi-item orders: {summary["baskets"]["multi_item_orders"]:,}; multi-distinct-product baskets: {summary["baskets"]["multi_distinct_product_orders"]:,}/{len(orders):,}.',
           f'- Top {c["top_one_percent_n_floor"]} sellers (floor 1% of {c["entities"]:,}) sold {c["top_one_percent_items"]:,}/{c["items"]:,} items ({c["top_one_percent_share"]:.2%}).',
           f'- Median observed delivery: {distribution(delivery_days).get("median", 0):.2f} days (n={len(delivery_days):,}).',
           '', '## Review counts — retention sensitivity',
           'Manual empty counts imply 40,641 non-empty messages and 11,517 titles on graph nodes, not 57,769 messages/12,531 titles. Source and first/last dedup are measured below; neither retention is assumed to match the graph.']
    md += [f'- {k}: {json.dumps(v)}' for k, v in review_sensitivity.items()]
    md += ['', '## Outputs', '- `p2_profile.json`: provenance hashes, checks, histograms, category concentration and temporal summaries.',
           '- `p2_null_rates.csv`: every source column with denominator, missing/empty counts and rates.', '', '## Limitations']
    md += ['- ' + x for x in summary['limitations']]
    if failures:
        md += ['', '## Failed checks'] + ['- ' + x for x in failures]
    (REPORTS / 'p2_profile_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'Checks={len(facts)} failures={len(failures)}; source-only report ready', flush=True)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
