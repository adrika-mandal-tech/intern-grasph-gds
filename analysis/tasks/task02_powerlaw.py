"""Phase 2 — power-law fit with goodness-of-fit and competing models (source CSV).

Run: python3 analysis/tasks/task02_powerlaw.py
Outputs analysis/reports/p2_powerlaw.json and p2_powerlaw_summary.md.

Method (Clauset–Shalizi–Newman style, continuous approximation):
  * xmin chosen by minimising the Kolmogorov–Smirnov distance over candidate xmins;
  * exponent by maximum likelihood (Hill);
  * goodness-of-fit p-value by a semi-parametric bootstrap with xmin held fixed;
  * power law compared against lognormal and exponential by a per-point
    log-likelihood-ratio (Vuong) test on the tail.

All distributions are discrete (counts), so the continuous fit is an approximation;
this is stated in the report rather than hidden. Counts and denominators are printed
next to every score. No graph claim is made: these are source CSV incidences.
"""
import csv
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT.parent / 'Olist-Kaggle-dataset'
REPORTS = ROOT / 'reports'
SEED = 20261009
BOOTSTRAP_REPS = 300
MIN_TAIL = 50


def load(name, columns):
    with (CSV_DIR / name).open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            yield {c: row[c] for c in columns}


def alpha_mle(tail, xmin):
    tail = np.asarray(tail, dtype=float)
    return 1.0 + len(tail) / np.sum(np.log(tail / xmin))


def ks_distance(tail, xmin, alpha):
    tail = np.sort(np.asarray(tail, dtype=float))
    n = len(tail)
    cdf = 1.0 - (tail / xmin) ** (-(alpha - 1.0))
    i = np.arange(n)
    return float(max(np.max(np.abs(cdf - i / n)), np.max(np.abs((i + 1) / n - cdf))))


def fit(x, xmins=None):
    x = np.asarray(sorted(x), dtype=float)
    candidates = xmins if xmins is not None else np.unique(x)
    best = None
    for xmin in candidates:
        tail = x[x >= xmin]
        if len(tail) < MIN_TAIL or xmin <= 0:
            continue
        alpha = alpha_mle(tail, xmin)
        d = ks_distance(tail, xmin, alpha)
        if best is None or d < best['D']:
            best = {'xmin': float(xmin), 'alpha': float(alpha), 'D': d,
                    'n_tail': int(len(tail))}
    return best


def bootstrap_p(x, xmin, alpha, d, reps=BOOTSTRAP_REPS, seed=SEED):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    below = x[x < xmin]
    n = len(x)
    ptail = np.mean(x >= xmin)
    hits = 0
    for _ in range(reps):
        n_tail = rng.binomial(n, ptail)
        tail = xmin * (1.0 - rng.random(n_tail)) ** (-1.0 / (alpha - 1.0))
        if len(below):
            body = rng.choice(below, size=n - n_tail, replace=True)
        else:
            body = np.empty(n - n_tail)
        synth = np.concatenate([body, tail])
        b = fit(synth, xmins=[xmin])
        if b is None:
            continue
        if b['D'] >= d:
            hits += 1
    return hits / reps


def vuong(tail, xmin, alpha):
    """Return (R, p) for power law vs normalised lognormal and exponential."""
    tail = np.asarray(tail, dtype=float)
    n = len(tail)
    pl = np.log(alpha - 1.0) - math.log(xmin) - alpha * np.log(tail / xmin)
    out = {}
    for name, dist in (('lognormal', stats.lognorm), ('exponential', stats.expon)):
        params = dist.fit(tail, floc=0)
        ln = dist.logpdf(tail, *params)
        diff = pl - ln
        r = float(np.mean(diff))
        sigma = float(np.std(diff, ddof=1))
        if sigma == 0:
            out[name] = {'R': r, 'p': None}
        else:
            z = r * math.sqrt(n) / sigma
            out[name] = {'R': r, 'p': float(math.erfc(abs(z) / math.sqrt(2)))}
    return out


def top_share(x, fraction=0.01):
    vals = sorted(x, reverse=True)
    k = max(1, math.floor(len(vals) * fraction)) if vals else 0
    total = sum(vals)
    return {'entities': len(vals), 'items': total, 'top_n': k,
            'top_share': sum(vals[:k]) / total if total else None}


def analyse(name, values, denominator_note):
    values = [int(v) for v in values if v is not None]
    result = {'distribution': name, 'n': len(values),
              'denominator': denominator_note, 'counts': top_share(values)}
    best = fit(values)
    if best is None:
        result['fit'] = None
        result['note'] = f'fewer than {MIN_TAIL} values above any candidate xmin'
        print(f'{name}: n={len(values)} -> no power-law fit ({result["note"]})', flush=True)
        return result
    tail = [v for v in values if v >= best['xmin']]
    best['goodness_of_fit_p'] = bootstrap_p(values, best['xmin'], best['alpha'], best['D'])
    best['competitors'] = vuong(tail, best['xmin'], best['alpha'])
    result['fit'] = best
    print(f'{name}: n={len(values)} tail={best["n_tail"]} xmin={best["xmin"]:g} '
          f'alpha={best["alpha"]:.3f} KS={best["D"]:.4f} p={best["goodness_of_fit_p"]:.3f}',
          flush=True)
    for comp, stat in best['competitors'].items():
        p = stat['p']
        print(f'    vs {comp:12s} R={stat["R"]:+.4f} p={"n/a" if p is None else f"{p:.3f}"}',
              flush=True)
    return result


def main():
    REPORTS.mkdir(exist_ok=True)

    seller_items = Counter()
    product_items = Counter()
    categories = []
    for r in load('olist_order_items_dataset.csv',
                  ['product_id', 'seller_id']):
        seller_items[r['seller_id']] += 1
        product_items[r['product_id']] += 1
    for r in load('olist_products_dataset.csv', ['product_category_name']):
        categories.append(r['product_category_name'])
    person_orders = Counter(r['customer_unique_id'] for r in
                            load('olist_customers_dataset.csv', ['customer_unique_id']))
    order_items = Counter()
    for r in load('olist_order_items_dataset.csv', ['order_id']):
        order_items[r['order_id']] += 1

    distributions = {
        'seller_item_incidence': (list(seller_items.values()),
                                  f'{len(seller_items):,} sellers with >=1 item'),
        'product_item_incidence': (list(product_items.values()),
                                   f'{len(product_items):,} products sold in >=1 item'),
        'person_order_count': (list(person_orders.values()),
                               f'{len(person_orders):,} unique people (customer_unique_id)'),
        'order_item_count': (list(order_items.values()),
                             f'{len(order_items):,} orders with >=1 item'),
    }

    results = [analyse(name, values, note)
               for name, (values, note) in distributions.items()]

    report = {
        'source': 'Raw local CSVs; NOT a verified Grasph graph snapshot',
        'method': 'Clauset-Shalizi-Newman continuous power-law fit; xmin by KS; '
                  'exponent by MLE; p by semi-parametric bootstrap; '
                  'competitors by per-point log-likelihood-ratio (Vuong)',
        'seed': SEED, 'bootstrap_reps': BOOTSTRAP_REPS, 'min_tail': MIN_TAIL,
        'limitations': [
            'Counts are discrete; the continuous power law is an approximation.',
            'Item incidence is not projected graph degree.',
            'A large goodness-of-fit p does not prove a power law; it fails to reject it.',
            'Person order counts are right-censored: the window ends 2018-08.',
            'Lognormal/exponential fits use maximum likelihood with location fixed at 0.',
        ],
        'distributions': results,
    }
    (REPORTS / 'p2_powerlaw.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    md = ['# Phase 2 — power-law fits (source CSV)', '',
          '**Source-only: NOT a verified Grasph graph export.**', '',
          f'Method: {report["method"]}. Bootstrap reps: {BOOTSTRAP_REPS}, seed {SEED}.', '',
          '## Fits']
    for res in results:
        fit_ = res['fit']
        if fit_ is None:
            md.append(f'- **{res["distribution"]}** (n={res["n"]:,}): {res["note"]}.')
            continue
        comp = fit_['competitors']
        md.append(
            f'- **{res["distribution"]}** (n={res["n"]:,}, {res["denominator"]}): '
            f'tail={fit_["n_tail"]:,}, xmin={fit_["xmin"]:g}, alpha={fit_["alpha"]:.3f}, '
            f'KS D={fit_["D"]:.4f}, p={fit_["goodness_of_fit_p"]:.3f}.')
        for name, stat in comp.items():
            p = stat['p']
            md.append(f'  - vs {name}: R={stat["R"]:+.4f}, '
                      f'p={"n/a" if p is None else f"{p:.3f}"}.')
        c = res['counts']
        md.append(f'  - concentration: top {c["top_n"]} of {c["entities"]:,} '
                  f'({c["top_share"]:.2%}) account for {c["items"]:,} items.')
    md += ['', '## Limitations'] + ['- ' + x for x in report['limitations']]
    (REPORTS / 'p2_powerlaw_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('power-law report ready', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
