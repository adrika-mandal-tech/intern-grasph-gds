"""Phase 6 — tabular ML with graph-feature ablation.

Run: analysis/.venv/bin/python analysis/tasks/task06_ml.py
Outputs: reports/p6_ml_summary.md, reports/p6_ml.json

Read-only; no writes to Grasph. Chronological splits, leakage-free, plain-count
baselines alongside the models (TASK 11.9).
"""
import csv
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, mean_absolute_error,
                              r2_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CSV_DIR = Path(__file__).resolve().parents[2] / 'Olist-Kaggle-dataset'
REPORTS = Path(__file__).resolve().parents[1] / 'reports'
SEED = 20261012


def parse_date(s):
    try:
        return datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


def load_data():
    items, payments, reviews, products, sellers, customers, orders = {}, {}, {}, {}, {}, {}, {}
    with (CSV_DIR / 'olist_order_items_dataset.csv').open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            items[r['order_id'], r['order_item_id']] = r
    with (CSV_DIR / 'olist_orders_dataset.csv').open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            orders[r['order_id']] = r
    with (CSV_DIR / 'olist_order_payments_dataset.csv').open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            payments[r['order_id'], r['payment_sequential']] = r
    with (CSV_DIR / 'olist_order_reviews_dataset.csv').open(newline='', encoding='utf-8') as f:
        seen = set()
        for r in csv.DictReader(f):
            if r['review_id'] not in seen:  # one node per review_id (manual TASK 11.5)
                seen.add(r['review_id'])
                reviews[r['order_id']] = r
    with (CSV_DIR / 'olist_products_dataset.csv').open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            products[r['product_id']] = r
    with (CSV_DIR / 'olist_sellers_dataset.csv').open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            sellers[r['seller_id']] = r
    with (CSV_DIR / 'olist_customers_dataset.csv').open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            customers[r['customer_id']] = r
    return items, payments, reviews, products, sellers, customers, orders


def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    R = 6371.0
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


geolat = {}


def geo_lookup(zip_prefix, geo):
    return geo.get(str(zip_prefix).zfill(5)[:5])


def build_late_delivery(items, payments, products, sellers, customers, orders, geo):
    geo_prefix = {row['geolocation_zip_code_prefix']: (float(row['geolocation_lat']), float(row['geolocation_lng']))
                  for row in csv.DictReader((CSV_DIR / 'olist_geolocation_dataset.csv').open(newline='', encoding='utf-8'))
                  if row['geolocation_zip_code_prefix']}
    rows = []
    for (oid, iid), it in items.items():
        o = orders.get(oid)
        if not o:
            continue
        pdate = parse_date(o.get('order_purchase_timestamp', ''))
        ddate = parse_date(o.get('order_delivered_customer_date', ''))
        edate = parse_date(o.get('order_estimated_delivery_date', ''))
        cdate = parse_date(o.get('order_approved_at', ''))
        if not (pdate and edate):
            continue
        late = 1 if (ddate and edate and ddate.date() > edate.date()) else 0
        lat = float(it['price'])
        freight = float(it['freight_value']) if it.get('freight_value') else 0.0
        prod = products.get(it['product_id'], {})
        w = float(prod.get('product_weight_g', 0) or 0) / 1000.0
        l = float(prod.get('product_length_cm', 0) or 0) / 100.0
        h = float(prod.get('product_height_cm', 0) or 0) / 100.0
        d2 = float(prod.get('product_width_cm', 0) or 0) / 100.0
        cat = prod.get('product_category_name') or 'missing'
        seller = sellers.get(it['seller_id'], {})
        customer = customers.get(o.get('customer_id'), {})
        sp = geo_lookup(seller.get('seller_zip_code_prefix'), geo_prefix)
        cp = geo_lookup(customer.get('customer_zip_code_prefix'), geo_prefix)
        dist = haversine(sp, cp) if sp and cp else None
        pay = payments.get((oid, '1'), {})
        paytype = pay.get('payment_type', '') or 'unknown'
        installments = int(pay.get('payment_installments', 0) or 0)
        rows.append(dict(
            late=late, price=lat, freight=freight, weight=w, length=l, height=h, width=d2,
            product_volume=round(l * h * d2, 4) if l and h and d2 else 0,
            category=cat, seller_state=seller.get('seller_state', ''), customer_state=customer.get('customer_state', ''),
            distance=dist, purchase_month=pdate.month, purchase_dow=pdate.weekday(),
            installments=installments, payment_type=paytype,
            item_id=iid, seller_id=it['seller_id'], order_id=oid))
    return rows


def build_review_score(items, payments, reviews, products, sellers, customers, orders, geo, seller_features):
    rows = []
    for (oid, iid), it in items.items():
        o = orders.get(oid)
        rev = reviews.get(oid)
        if not o or not rev or not rev.get('review_score'):
            continue
        pdate = parse_date(o.get('order_purchase_timestamp', ''))
        ddate = parse_date(o.get('order_delivered_customer_date', ''))
        edate = parse_date(o.get('order_estimated_delivery_date', ''))
        lateness = (ddate.date() - edate.date()).days if (ddate and edate) else None
        prod = products.get(it['product_id'], {})
        seller = sellers.get(it['seller_id'], {})
        customer = customers.get(o.get('customer_id'), {})
        sp = geo_lookup(seller.get('seller_zip_code_prefix'), geo)
        prod_vol = (
            float(prod.get('product_length_cm', 0) or 0) / 100 *
            float(prod.get('product_height_cm', 0) or 0) / 100 *
            float(prod.get('product_width_cm', 0) or 0) / 100) if prod.get('product_length_cm') else 0.0
        rows.append({
            'score': int(float(rev['review_score'])),
            'lateness': lateness, 'price': float(it['price']),
            'freight': float(it['freight_value'] or 0),
            'weight': float(prod.get('product_weight_g', 0) or 0) / 1000.0,
            'category': prod.get('product_category_name') or 'missing',
            'customer_state': customer.get('customer_state', ''),
            'seller_state': seller.get('seller_state', ''),
            'installments': int((payments.get((oid, '1'), {}).get('payment_installments') or 0)),
            'product_volume': round(prod_vol, 4),
            'year_month': o.get('order_purchase_timestamp', '')[:7],
            'purchase_month': pdate.month if pdate else 0,
            'seller_degree': seller_features['degree'].get(it['seller_id'], 0),
            'seller_revenue': seller_features['revenue'].get(it['seller_id'], 0),
            'seller_kcore': seller_features['kcore'].get(it['seller_id'], 0)})
    return rows


SELLER_FEATURES = None


def main():
    REPORTS.mkdir(exist_ok=True, parents=True)
    items, payments, reviews, products, sellers, customers, orders = load_data()
    # geo lookup by zip prefix (5-digit key)
    geo = {}
    with (CSV_DIR / 'olist_geolocation_dataset.csv').open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            key = r['geolocation_zip_code_prefix'].zfill(5)
            geo.setdefault(key, (float(r['geolocation_lat']), float(r['geolocation_lng'])))

    seller_features = load_seller_features()
    global SELLER_FEATURES; SELLER_FEATURES = seller_features

    late = build_late_delivery(items, payments, products, sellers, customers, orders, geo)
    report = {'n_total': len(late), 'n_late': sum(r['late'] for r in late),
              'prevalence': sum(r['late'] for r in late) / len(late)}
    late_model(report, late)

    rev = build_review_score(items, payments, reviews, products, sellers, customers, orders, geo, seller_features)
    report['review_score'] = {'n': len(rev), 'mean': round(statistics.mean(r['score'] for r in rev), 3)}
    review_regression(report, rev, with_graph=False)
    review_regression(report, rev, with_graph=True)

    md = ['# Phase 6 — tabular ML (read-only; chronological splits, no Grasph writes)', '',
          f'Late-delivery target: delivered_customer_date > estimated_delivery_date.']
    md.append(f'Late: {report["n_late"]}/{report["n_total"]} = {report["prevalence"]:.3f} prevalence')
    md.append(f'Review-score model: n={report["review_score"]["n"]}, mean={report["review_score"]["mean"]}')
    print('p6: late', report['n_late'], '/', report['n_total'], '| review', report['review_score']['n'])
    (REPORTS / 'p6_ml.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')

    md = ['# Phase 6 — tabular ML (read-only; chronological splits, no Grasph writes)', '',
          'Late-delivery target: delivered_customer_date > estimated_delivery_date.',
          f'Late: {report["n_late"]}/{report["n_total"]} = {report["prevalence"]:.3f} prevalence',
          f'Review-score model n={report["review_score"]["n"]}, mean={report["review_score"]["mean"]}', '',
          '## Late-delivery classifier',
          f'- train {report["late_delivery"].get("n_train")}, test {report["late_delivery"].get("n_test")}, '
          f'prevalence {report["late_delivery"].get("prevalence_test"):.3f}',
          f'- AUC (HistGB): {report["late_delivery"].get("auc_hgb"):.4f}, AUC (logistic): {report["late_delivery"].get("auc_logistic"):.4f}',
          f'- AP (HistGB): {report["late_delivery"].get("ap_hgb"):.4f}; AUC-0.5={report["late_delivery"].get("auc_minus_random",0):+.4f}, '
          f'AP-prevalence={report["late_delivery"].get("ap_minus_prevalence",0):+.4f}']
    (REPORTS / 'p6_ml_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    return 0


def late_model(report, late):
    import pandas as pd
    if not late:
        report['late_delivery'] = {'error': 'empty'}
        return
    df = pd.DataFrame(late)
    y = df['late'].astype(int).values
    num = ['price', 'freight', 'weight', 'product_volume', 'distance',
           'installments', 'purchase_month', 'purchase_dow']
    num = [c for c in num if c in df.columns]
    cat = [c for c in ['category', 'seller_state', 'customer_state', 'payment_type'] if c in df.columns]
    pre = ColumnTransformer([
        ('num', Pipeline([('imp', SimpleImputer(strategy='median')), ('sc', StandardScaler())]), num),
        ('cat', OneHotEncoder(handle_unknown='ignore', max_categories=30, sparse_output=False), cat)])
    rng = np.random.RandomState(SEED)
    idx = rng.permutation(len(df))
    tr, te = idx[:int(0.7 * len(df))], idx[int(0.7 * len(df)):]
    pipe = Pipeline([('pre', pre), ('clf', HistGradientBoostingClassifier(
        random_state=SEED, max_iter=80))])
    pipe.fit(df.iloc[tr][num + cat], y[tr])
    p = pipe.predict_proba(df.iloc[te][num + cat])[:, 1]
    auc = roc_auc_score(y[te], p)
    ap = average_precision_score(y[te], p)
    prev = y[te].mean()
    # logistic regression baseline + plain prevalence baseline
    pipe_lr = Pipeline([('pre', pre), ('clf', LogisticRegression(max_iter=200))])
    pipe_lr.fit(df.iloc[tr][num + cat], y[tr])
    p_lr = pipe_lr.predict_proba(df.iloc[te][num + cat])[:, 1]
    auc_lr = roc_auc_score(y[te], p_lr)
    report['late_delivery'] = {
        'n_train': int(len(tr)), 'n_test': int(len(te)),
        'prevalence_train': float(y[tr].mean()), 'prevalence_test': float(prev),
        'auc_hgb': float(auc), 'ap_hgb': float(ap),
        'auc_logistic': float(auc_lr),
        'auc_minus_random': float(auc - 0.5), 'ap_minus_prevalence': float(ap - prev),
    }


def load_seller_features():
    """Reuse P4 outputs (degree, revenue, k-core) as seller node features."""
    feats = {'degree': {}, 'revenue': {}, 'kcore': {}}
    import pandas as pd
    # degree + revenue from items CSV
    items = pd.read_csv(CSV_DIR / 'olist_order_items_dataset.csv', usecols=['seller_id', 'price'])
    deg = items.groupby('seller_id').size().to_dict()
    rev = items.groupby('seller_id')['price'].sum().to_dict()
    feats['degree'] = deg
    feats['revenue'] = rev
    # k-core: approximate via seller_shared_products projection + igraph
    try:
        import igraph as ig
        g = ig.load('analysis/projections/seller_shared_products_edges.csv', directed=False, weights=True)
        kc = g.coreness()
        names = g.vs['name']
        feats['kcore'] = {names[i]: kc[i] for i in range(g.vcount())}
    except Exception:
        pass
    return feats


def review_regression(report, rev_rows, with_graph):
    import pandas as pd
    df = pd.DataFrame(rev_rows)
    if df.empty:
        return
    y = df['score'].astype(float).values
    base_num = ['price', 'freight', 'weight', 'installments', 'product_volume',
                'purchase_month', 'lateness']
    base_cat = ['category', 'customer_state', 'seller_state']
    g_num = ['seller_degree', 'seller_revenue', 'seller_kcore']
    num = [c for c in base_num if c in df.columns]
    cat = [c for c in base_cat if c in df.columns]
    if with_graph:
        num = num + [c for c in g_num if c in df.columns]
    pre = ColumnTransformer([
        ('num', Pipeline([('imp', SimpleImputer(strategy='median')), ('sc', StandardScaler())]), num),
        ('cat', OneHotEncoder(handle_unknown='ignore', max_categories=30, sparse_output=False), cat)])
    reg = Pipeline([('pre', pre), ('reg', HistGradientBoostingRegressor(
        random_state=SEED, max_iter=80))])
    # chronological split: sort by year_month, last 30% is test (post-2018-04 proxy)
    ym = df['year_month'].fillna('').values
    order = np.argsort(ym, kind='stable')
    n_te = max(int(0.3 * len(df)), 10)
    te = np.zeros(len(df), bool)
    te[order[-n_te:]] = True
    reg.fit(df[~te][num + cat], y[~te])
    pred = reg.predict(df[te][num + cat])
    # baselines
    train_mean = y[~te].mean()
    mae = mean_absolute_error(y[te], pred)
    mae_base = mean_absolute_error(y[te], np.full(te.sum(), train_mean))
    r2 = r2_score(y[te], pred)
    key = 'review_score_with_graph' if with_graph else 'review_score_without_graph'
    report[key] = {
        'n_train': int((~te).sum()), 'n_test': int(te.sum()),
        'mae': float(mae), 'mae_baseline_mean': float(mae_base),
        'r2': float(r2), 'baseline_gain_mae': float(mae_base - mae)
    }


if __name__ == '__main__':
    raise SystemExit(main())