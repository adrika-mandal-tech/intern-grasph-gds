"""Phase 5 — temporal link prediction + association rules.

Run: python3 analysis/tasks/task05_link_prediction.py
Outputs: analysis/reports/p5_link_prediction.json, _summary.md
"""
import csv
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT.parent / 'Olist-Kaggle-dataset'
PROJ = ROOT / 'projections'
REPORTS = ROOT / 'reports'
SEEDS = list(range(5))
SPLIT = '2018-06-01'  # freeze train before this


def load_items():
    items = []
    with (CSV_DIR / 'olist_order_items_dataset.csv').open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            items.append({
                'order_id': row['order_id'],
                'product_id': row['product_id'],
                'seller_id': row['seller_id'],
            })
    return items


def load_orders():
    orders = {}
    with (CSV_DIR / 'olist_orders_dataset.csv').open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            orders[row['order_id']] = row['order_purchase_timestamp'][:10]
    return orders


def build_graphs(items, orders):
    """Build train (before split) and test (after split) GRAPHS (neighbor sets).

    seller-seller (shared products): edge (s1,s2) if both sell the same product.
    An edge is a TRAIN edge if any shared product was first sold < SPLIT, and a
    TEST edge if any shared product was first sold >= SPLIT (a product sold in
    both windows counts for both).
    product-product (bought together): edge (p1,p2) if co-bought in an order before/after split.
    """
    from datetime import date
    # order -> seller / order -> product, labeled train/test
    train_os, test_os = defaultdict(set), defaultdict(set)
    train_op, test_op = defaultdict(set), defaultdict(set)
    product_sellers = defaultdict(lambda: defaultdict(set))  # product -> {True/False: set(sellers)}
    for it in items:
        o = it['order_id']; p = it['product_id']; s = it['seller_id']
        dt = orders.get(o, '')
        if dt < SPLIT:
            train_os[o].add(s); train_op[o].add(p)
            product_sellers[p][True].add(s)
        else:
            test_os[o].add(s); test_op[o].add(p)
            product_sellers[p][False].add(s)

    # seller-seller shared products: per product, pair sellers; split by first-seen window
    train_ss, test_ss = defaultdict(set), defaultdict(set)
    def add_pairs(sellers, train_d, test_d, key):
        ls = sorted(sellers)
        for i in range(len(ls)):
            for j in range(i + 1, len(ls)):
                if key:  train_d[ls[i]].add(ls[j]); train_d[ls[j]].add(ls[i])
                else:     test_d[ls[i]].add(ls[j]); test_d[ls[j]].add(ls[i])
    for p, sw in product_sellers.items():
        train_s = sw[True]; test_s = sw[False]
        both = train_s & test_s
        add_pairs(train_s, train_ss, test_ss, True)
        add_pairs(test_s, train_ss, test_ss, False)

    # product-product bought together: per order, pair products; split by order window
    train_pp, test_pp = defaultdict(set), defaultdict(set)
    for o, prods in train_op.items():
        ps = sorted(prods)
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                train_pp[ps[i]].add(ps[j]); train_pp[ps[j]].add(ps[i])
    for o, prods in test_op.items():
        ps = sorted(prods)
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                test_pp[ps[i]].add(ps[j]); test_pp[ps[j]].add(ps[i])

    return train_ss, test_ss, train_pp, test_pp



def score_cn(neigh_i, neigh_j):
    return len(neigh_i & neigh_j)


def score_jaccard(neigh_i, neigh_j):
    u = len(neigh_i | neigh_j)
    return len(neigh_i & neigh_j) / u if u else 0.0


def score_aa(neigh_i, neigh_j, deg):
    total = 0.0
    for z in neigh_i & neigh_j:
        d = deg.get(z, 2)
        if d > 1:
            total += 1.0 / math.log(d)
    return total


def score_pa(neigh_i, neigh_j, deg):
    return deg.get(next(iter(neigh_i), None), 0) * deg.get(next(iter(neigh_j), None), 0) if neigh_i and neigh_j else 0


def evaluate_link_pred(train_neigh, test_neigh, name):
    """Compute CN, Jaccard, AA, PA for all non-edges in train, rank against test edges."""
    nodes = list(train_neigh.keys())
    deg = {n: len(train_neigh[n]) for n in nodes}
    train_edges = set()
    for u, vs in train_neigh.items():
        for v in vs:
            if u < v:
                train_edges.add((u, v))
    test_edges = set()
    for u, vs in test_neigh.items():
        for v in vs:
            if u < v:
                test_edges.add((u, v))
    test_edges = {(u, v) for u, v in test_edges if u in train_neigh and v in train_neigh}
    if not test_edges:
        return {'error': 'no test edges in train node set'}

    # candidate non-edges
    candidates = []
    test_set = set(test_edges)
    for i, u in enumerate(nodes):
        for v in nodes[i + 1:]:
            if (u, v) not in train_edges:
                candidates.append((u, v))
    # sample candidates if too many
    rng = np.random.default_rng(SEEDS[0])
    if len(candidates) > 200000:
        candidates = [candidates[i] for i in rng.choice(len(candidates), 200000, replace=False)]

    labels = []
    scores = {k: [] for k in ['CN', 'Jaccard', 'AA', 'PA']}
    for u, v in candidates:
        neigh_u, neigh_v = train_neigh[u], train_neigh[v]
        labels.append(1 if (u, v) in test_set else 0)
        scores['CN'].append(score_cn(neigh_u, neigh_v))
        scores['Jaccard'].append(score_jaccard(neigh_u, neigh_v))
        scores['AA'].append(score_aa(neigh_u, neigh_v, deg))
        scores['PA'].append(score_pa(neigh_u, neigh_v, deg))

    y = np.array(labels)
    results = {'name': name, 'candidates': len(candidates), 'test_edges': len(test_edges),
               'prevalence': float(y.mean())}
    for k, s in scores.items():
        s = np.array(s)
        if s.std() == 0:
            results[k] = {'auc': 0.5, 'ap': y.mean()}
            continue
        auc = stats.mannwhitneyu(s[y == 1], s[y == 0], alternative='greater').statistic / (y.sum() * (len(y) - y.sum()))
        ap = 0.0
        for thresh in np.unique(s)[::-1]:
            pred = s >= thresh
            tp = (pred & (y == 1)).sum()
            fp = (pred & (y == 0)).sum()
            if tp == 0:
                continue
            precision = tp / (tp + fp)
            recall = tp / y.sum()
            ap += precision * (recall - 0)  # simplified; full AP needs sorted by score
        # proper AP via sklearn-like
        order = np.argsort(-s)
        y_sorted = y[order]
        precisions = np.cumsum(y_sorted) / np.arange(1, len(y_sorted) + 1)
        ap = np.mean(precisions[y_sorted == 1]) if y.sum() else 0.0
        results[k] = {'auc': float(auc), 'ap': float(ap)}
    return results


def association_rules(baskets, min_sup=0.01, min_conf=0.5, n_total=None):
    """Simple Apriori on baskets; returns rules with support over multi-baskets AND all orders."""
    itemsets = defaultdict(int)
    N = len(baskets)
    for b in baskets:
        for item in b:
            itemsets[frozenset([item])] += 1
    freq = {s: c for s, c in itemsets.items() if c / N >= min_sup}
    k = 2
    while freq:
        new = defaultdict(int)
        items = list(freq.keys())
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                union = items[i] | items[j]
                if len(union) == k:
                    count = sum(1 for b in baskets if union <= b)
                    if count / N >= min_sup:
                        new[union] = count
        if not new:
            break
        freq.update(new)
        k += 1
    rules = []
    for itemset, count in freq.items():
        if len(itemset) < 2:
            continue
        for item in itemset:
            antecedent = frozenset([item])
            consequent = itemset - antecedent
            if not consequent:
                continue
            ant_count = sum(1 for b in baskets if antecedent <= b)
            cons_count = sum(1 for b in baskets if consequent <= b)
            conf = count / ant_count if ant_count else 0
            lift = conf / (cons_count / N) if cons_count else float('inf')
            if conf >= min_conf:
                rules.append({
                    'antecedent': list(antecedent), 'consequent': list(consequent),
                    'support_cond': count / N, 'support_all_orders': count / n_total if n_total else None,
                    'confidence': conf, 'lift': lift, 'count_in_multi': count
                })
    rules.sort(key=lambda r: -r['lift'])
    return rules[:20], N, n_total


def main():
    REPORTS.mkdir(exist_ok=True)
    items = load_items()
    orders = load_orders()
    train_ss, test_ss, train_pp, test_pp = build_graphs(items, orders)
    np.random.seed(SEEDS[0])

    # seller-seller link prediction
    res_ss = evaluate_link_pred(train_ss, test_ss, 'seller_shared_products')
    # product-product link prediction
    res_pp = evaluate_link_pred(train_pp, test_pp, 'product_bought_together')

    # association rules on multi-distinct-product orders
    baskets = []
    for it in items:
        pass
    order_prods = defaultdict(set)
    for it in items:
        order_prods[it['order_id']].add(it['product_id'])
    multi_baskets = [prods for prods in order_prods.values() if len(prods) >= 2]
    n_total = len(order_prods)
    rules, n_multi, N_orders = association_rules(multi_baskets, min_sup=0.001, min_conf=0.2,
                                                  n_total=n_total)

    report = {
        'split_date': SPLIT,
        'seller_seller': res_ss,
        'product_product': res_pp,
        'association_rules': {
            'n_multi_baskets': n_multi, 'n_total_orders': N_orders,
            'top_rules': rules
        }
    }
    (REPORTS / 'p5_link_prediction.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    md = ['# Phase 5 — temporal link prediction & association rules', '',
          f'Time split: train < {SPLIT}, test >= {SPLIT}', '',
          '## Seller–seller (shared products)', f'- candidates: {res_ss.get("candidates", "N/A")}, '
          f'test edges: {res_ss.get("test_edges", 0)}, prevalence: {res_ss.get("prevalence", 0):.4f}']
    for k in ['CN', 'Jaccard', 'AA', 'PA']:
        v = res_ss.get(k, {})
        md.append(f'  - {k}: AUC={v.get("auc", 0):.4f}, AP={v.get("ap", 0):.4f}')
    md.append('')
    md.append('## Product–product (bought together)')
    for k in ['CN', 'Jaccard', 'AA', 'PA']:
        v = res_pp.get(k, {})
        md.append(f'  - {k}: AUC={v.get("auc", 0):.4f}, AP={v.get("ap", 0):.4f}')
    md.append('')
    md.append('## Association rules (multi-product baskets)')
    md.append(f'- multi-distinct-product orders: {n_multi} / {N_orders} total orders')
    for r in rules[:10]:
        md.append(f'  - {r["antecedent"]} -> {r["consequent"]}: '
                  f'sup_cond={r["support_cond"]:.4f}, conf={r["confidence"]:.3f}, lift={r["lift"]:.2f}')
    (REPORTS / 'p5_link_prediction_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('p5 done')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())