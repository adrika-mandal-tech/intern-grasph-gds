"""Phase 7 — NLP: Portuguese review sentiment vs score, near-duplicates.

Run: python3 analysis/tasks/task07_nlp.py
Outputs: reports/p7_nlp_summary.md, reports/p7_nlp.json

No external model download (BERTimbau is network-bound and heavy). A compact
Portuguese sentiment lexicon gives a deterministic consistency baseline; the
report flags BERTimbau as the upgrade path. Near-duplicates via shingled
MinHash/Jaccard on tokens.
"""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

CSV_DIR = Path(__file__).resolve().parents[2] / 'Olist-Kaggle-dataset'
REPORTS = Path(__file__).resolve().parents[1] / 'reports'
SEED = 20261012

POSITIVE = set("""excelente otimo otimo ótimo ótimo excelente maravilhoso adoro adoravel 
fantastico incrivel incrível sensacional ótimo bom sim ótimo perfeito perfeito nota10 nota 
10 010 recomendaria recomendo super recomendado positivo positivo ótima ótimo""".split())
NEGATIVE = set("""ruim péssimo terrivel pior piora horrivel nojento ruim defeito travou travou 
atraso atrasado atrasada quebrado quebrada vazio falso falsificação lento lenta demora 
demorou decepção decepcionado decepcionante problema erro bug não não recomendo ruim""".split())


def tokenize(text):
    return re.findall(r"[a-záéíóúâêîôãõç]+", text.lower())


def sentiment(text):
    toks = tokenize(text)
    if not toks:
        return 0.0
    pos = sum(1 for t in toks if t in POSITIVE)
    neg = sum(1 for t in toks if t in NEGATIVE)
    n = len(toks)
    if n == 0:
        return 0.0
    return (pos - neg) / n  # in [-1, 1]


def jaccard(a, b):
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def reviews():
    seen = {}
    with (CSV_DIR / 'olist_order_reviews_dataset.csv').open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['review_id'] not in seen:  # one node per review_id (manual TASK 11.5)
                seen[r['review_id']] = r
    return list(seen.values())


def main():
    REPORTS.mkdir(exist_ok=True, parents=True)
    revs = reviews()
    n_total = len(revs)
    with_msg = [r for r in revs if r.get('review_comment_message', '').strip()]
    n_msg = len(with_msg)
    with_title = [r for r in revs if r.get('review_comment_title', '').strip()]

    # sentiment vs score
    by_score = defaultdict(list)
    inconsistencies = []
    for r in with_msg:
        try:
            score = int(float(r['review_score']))
        except Exception:
            continue
        sent = sentiment(r['review_comment_message'])
        by_score[score].append(sent)
        # define inconsistency: 5-star with negative sentiment, 1/2-star with positive
        if score >= 4 and sent < -0.15:
            inconsistencies.append(('5star_neg', score, sent, r['review_comment_message'][:80]))
        elif score <= 2 and sent > 0.15:
            inconsistencies.append(('1star_pos', score, sent, r['review_comment_message'][:80]))

    mean_by_score = {s: round(float(np.mean(v)), 3) for s, v in sorted(by_score.items())}
    # Spearman correlation sentiment vs score across all scored rows
    rows_sc = []
    for r in with_msg:
        sc = r['review_score']
        if sc and sc.strip() in {'1', '2', '3', '4', '5'}:
            rows_sc.append((int(sc), sentiment(r['review_comment_message'])))

    if len(rows_sc) >= 3:
        scores = np.array([x[0] for x in rows_sc])
        sents = np.array([x[1] for x in rows_sc])
        rho, p = _spearman(scores, sents)
    else:
        rho, p = 0.0, 1.0

    # near-duplicate detection via minhash on token shingles (5-minhash)
    rng = np.random.default_rng(SEED)
    hashes = []
    for r in with_msg:
        toks = tokenize(r['review_comment_message'])
        if not toks:
            continue
        shingles = set(zip(toks, toks[1:])) if len(toks) > 1 else {('^', toks[0], '$')}
        if not shingles:
            shingles = {(toks[0],)}
        # minhash: hash each shingle with 5 random linear functions over a large prime
        rows = np.array([hash(s) & 0x7fffffff for s in shingles])
        if len(rows) == 0:
            continue
        sig = []
        for i in range(5):
            a, b = rng.integers(1, 1 << 20, 2)
            sig.append(((a * rows + b) % 2147483647).min())
        hashes.append((sig, r['review_id']))

    # find candidate near-duplicate pairs with > 50% minhash bands matching
    dup_pairs = 0
    checked = 0
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            checked += 1
            sig_i, sig_j = hashes[i][0], hashes[j][0]
            match = sum(1 for a, b in zip(sig_i, sig_j) if a == b) / 5
            if match > 0.4:
                dup_pairs += 1
    dup_rate = dup_pairs / max(checked, 1)

    # duplicate review_id across orders
    rev_order_counts = Counter(r.get('review_id') for r in with_msg)
    multi_review = sum(1 for v in rev_order_counts.values() if v > 1)

    report = {
        'n_reviews_unique_id': n_total,
        'n_with_message': n_msg,
        'n_with_title': len(with_title),
        'mean_sentiment_by_score': mean_by_score,
        'sentiment_vs_score_spearman_rho': float(rho),
        'sentiment_vs_score_p': float(p),
        'inconsistencies': len(inconsistencies),
        'sample_inconsistencies': inconsistencies[:5],
        'near_duplicate_pairs_found': dup_pairs,
        'near_duplicate_pairs_checked': checked,
        'near_duplicate_rate': round(dup_rate, 6),
        'duplicate_review_ids': multi_review,
    }
    (REPORTS / 'p7_nlp.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    md = ['# Phase 7 — Portuguese review NLP (lexicon baseline; BERTimbau is the upgrade path)', '',
          f'Reviews (unique review_id): {n_total}; with message: {n_msg}; with title: {len(with_title)}', '',
          '## Sentiment vs score',
          f'Mean lexicon sentiment by review score: {mean_by_score}',
          f'Spearman rho(sentiment, score) = {rho:.4f} (p={p:.2g}); inconsistencies = {len(inconsistencies)}',
          'Sample 5-star-negative-text reviews:']
    for tag, sc, sent, msg in inconsistencies[:5]:
        md.append(f'  - score={sc} sentiment={sent:.2f}: {msg}')
    md += ['', '## Near-duplicate review detection',
           f'- minhash candidate pairs checked: {checked:,}; near-dup pairs (>0.4 band match): {dup_pairs} '
           f'(rate {dup_rate:.6f})',
           f'- duplicate review_id across orders: {multi_review} (the known quirk; graph keeps one row)']
    (REPORTS / 'p7_nlp_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('p7 done: reviews', n_total, 'msg', n_msg, 'inconsistencies', len(inconsistencies), 'rho', rho)
    return 0


def _spearman(x, y):
    import pandas as pd
    from scipy import stats
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    xm, ym = rx.mean(), ry.mean()
    s = ((rx - xm) * (ry - ym)).sum() / np.sqrt(((rx - xm) ** 2).sum() * ((ry - ym) ** 2).sum())
    return s, stats.pearsonr(rx, ry)[1]


if __name__ == '__main__':
    raise SystemExit(main())
