"""Phase 4 — classical graph algorithms on the source-derived projections.

Run: analysis/.venv/bin/python analysis/tasks/task04_graph_algorithms.py
Outputs: analysis/reports/p4_graph_algorithms.json, _summary.md

Source-derived projections (NOT a verified Grasph export; the manual verifies
each node/relationship equals the source CSV with 0 differences, and every
count is cross-checked against the live Grasph server aggregates in
p1_verify_platform.json / task09).

TASK 11.9 rules applied: projection named with node/edge counts; stochastic
algorithms over 10 seeds with ranges; plain counts next to scores; null-model
permutation test; denominators stated.
"""
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import igraph as ig
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJ = ROOT / 'projections'
REPORTS = ROOT / 'reports'
SEEDS = list(range(10))
NULL_REPS = 20


def load_projection(name):
    edges = []
    with (PROJ / f'{name}_edges.csv').open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            edges.append((row['source'], row['target'], float(row['weight'])))
    nodes = []
    with (PROJ / f'{name}_nodes.csv').open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['id'] not in nodes:
                nodes.append(row['id'])
    return nodes, edges


def build(name):
    nodes, edges = load_projection(name)
    g = ig.Graph()
    g.add_vertices([str(n) for n in nodes])
    index = {str(n): i for i, n in enumerate(g.vs['name'])}
    pairs, weights = [], []
    for s, t, w in edges:
        pairs.append((index[str(s)], index[str(t)]))
        weights.append(w)
    g.add_edges(pairs)
    g.es['weight'] = weights
    g.simplify(combine_edges={'weight': 'sum'})
    return g


def describe(g):
    comps = g.components(mode='WEAK')
    sizes = comps.sizes()
    giant = max(sizes)
    gc = comps.giant()
    degree = np.array(g.degree())
    return {
        'nodes': g.vcount(), 'edges': g.ecount(),
        'isolates': int((degree == 0).sum()),
        'components': len(sizes),
        'giant_component_nodes': int(giant),
        'giant_share': round(giant / g.vcount(), 4),
        'mean_degree': round(float(degree.mean()), 3),
        'max_degree': int(degree.max()),
        'mean_weighted_degree': round(float(np.array(g.strength(weights='weight')).mean()), 3),
        'diameter_giant': int(gc.diameter()) if gc.vcount() > 1 else 0,
        'aspl_giant': round(float(gc.average_path_length()), 4) if gc.vcount() > 1 else 0.0,
        'kcore_max': int(max(g.coreness())) if g.vcount() else 0,
    }


def louvain_runs(g, seeds=SEEDS):
    """Leiden over 10 seeds (seeded random initial membership; this igraph
    build exposes no RNG-seed argument, multilevel is deterministic)."""
    mods, sizes, parts = [], [], []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        init = rng.integers(0, max(2, g.vcount() // 50 + 1), size=g.vcount()).tolist()
        part = g.community_leiden(objective_function='modularity', weights='weight',
                                  n_iterations=2, initial_membership=init)
        mods.append(part.modularity)
        sizes.append(len(part))
        parts.append(part.membership)
    lp = []
    for seed in seeds[:5]:
        rng = np.random.default_rng(seed)
        init = rng.integers(0, g.vcount(), size=g.vcount()).tolist()
        lp.append(len(g.community_label_propagation(weights='weight', initial=init)))
    nmi = [ig.compare_communities(parts[0], p, method='nmi') for p in parts[1:]]
    return {
        'algorithm': 'leiden 10 seeds (seeded initial membership) + deterministic multilevel cross-check',
        'modularity_min': round(min(mods), 4), 'modularity_max': round(max(mods), 4),
        'modularity_mean': round(float(np.mean(mods)), 4),
        'multilevel_modularity': round(g.community_multilevel(weights='weight').modularity, 4),
        'n_communities_min': int(min(sizes)), 'n_communities_max': int(max(sizes)),
        'nmi_vs_seed0_min': round(min(nmi), 3), 'nmi_vs_seed0_max': round(max(nmi), 3),
        'label_propagation_n_communities_range': [int(min(lp)), int(max(lp))],
        'partitions_seed0': parts[0],
    }


def null_modularity(g, reps=NULL_REPS, seeds=SEEDS):
    """Degree-preserving rewiring (igraph double_edge_swap) keeps the degree
    sequence; Leiden on the randomized graphs gives the chance distribution."""
    base = g.copy()
    base.es['weight'] = [1.0] * base.ecount()  # degree-preserving null: unweighted modularity
    out = []
    for rep in range(reps):
        h = base.copy()
        try:
            h.rewire(n=10 * h.ecount() + 1)
            h.es['weight'] = [1.0] * h.ecount()  # rewire creates unweighted edges
        except Exception:
            continue
        part = h.community_leiden(objective_function='modularity', n_iterations=2,
                                  initial_membership=np.random.default_rng(rep).integers(
                                      0, max(2, h.vcount() // 50 + 1), size=h.vcount()).tolist())
        out.append(part.modularity)
    return out


def centrality_report(g, part=None):
    degree = np.array(g.degree())
    strength = np.array(g.strength(weights='weight'))
    pr = np.array(g.pagerank(weights='weight'))
    deg_order = np.argsort(-degree)
    pr_order = np.argsort(-pr)
    str_order = np.argsort(-strength)
    top = min(10, g.vcount())
    names = g.vs['name']
    from scipy.stats import spearmanr
    rho_deg, p_deg = spearmanr(degree, pr)
    rho_str, p_str = spearmanr(strength, pr)
    return {
        'pagerank_vs_degree_spearman': round(float(rho_deg), 4),
        'pagerank_vs_degree_p': float(p_deg),
        'pagerank_vs_weighted_degree_spearman': round(float(rho_str), 4),
        'top10_by_degree': [names[i] for i in deg_order[:top]],
        'top10_by_pagerank': [names[i] for i in pr_order[:top]],
        'top10_by_weighted_degree': [names[i] for i in str_order[:top]],
        'plain_count_matches': [names[i] for i in deg_order[:top]] == [names[i] for i in pr_order[:top]],
    }


def main():
    REPORTS.mkdir(exist_ok=True)
    report = {'source': 'source-derived projections; server aggregate cross-check separately', 'results': {}}
    md = ['# Phase 4 — graph algorithms on source-derived projections', '',
          'Read-only analysis; no writes to Grasph. Projections from task03 (name, nodes, edges in each section).',
          '']
    for name in ['seller_shared_products', 'seller_shared_categories', 'seller_co_order',
                 'product_bought_together', 'category_shared_sellers']:
        g = build(name)
        if g.ecount() == 0:
            continue
        desc = describe(g)
        entry = {'projection': name, **desc}
        md.append(f'## {name}: {desc["nodes"]} nodes, {desc["edges"]} edges')
        md.append(f'- components: {desc["components"]}, isolates: {desc["isolates"]}, '
                  f'giant: {desc["giant_component_nodes"]} ({desc["giant_share"]:.1%})')
        md.append(f'- mean degree {desc["mean_degree"]}, max {desc["max_degree"]}, '
                  f'k-core max {desc["kcore_max"]}, giant ASPL {desc["aspl_giant"]}, diameter {desc["diameter_giant"]}')
        # Louvain + null model on graphs where it is meaningful (not the near-bipartite tiny ones)
        if 0 < g.ecount() and desc['mean_degree'] > 1.5:
            lou = louvain_runs(g)
            nulls = null_modularity(g)
            obs = lou['modularity_mean']
            null_mean = float(np.mean(nulls)) if nulls else float('nan')
            null_sd = float(np.std(nulls)) if nulls else float('nan')
            p = (1 + sum(1 for x in nulls if x >= obs)) / (len(nulls) + 1) if nulls else float('nan')
            entry['louvain'] = {k: v for k, v in lou.items() if k != 'partitions_seed0'}
            entry['null_model'] = {'reps': len(nulls), 'null_modularity_mean': round(null_mean, 4),
                                   'null_modularity_sd': round(null_sd, 4),
                                   'permutation_p': round(p, 4)}
            md.append(f'- Louvain modularity {lou["modularity_min"]}–{lou["modularity_max"]} over 10 seeds, '
                      f'communities {lou["n_communities_min"]}–{lou["n_communities_max"]}, '
                      f'NMI vs seed0 {lou["nmi_vs_seed0_min"]}–{lou["nmi_vs_seed0_max"]}')
            md.append(f'- null (degree-preserving rewiring, {len(nulls)} reps): modularity {null_mean:.4f} ± {null_sd:.4f}, '
                      f'permutation p={p:.4f}')
        cen = centrality_report(g)
        entry['centrality'] = cen
        md.append(f'- PageRank vs degree Spearman rho={cen["pagerank_vs_degree_spearman"]} '
                  f'(p={cen["pagerank_vs_degree_p"]:.2g}); top-10 identical to plain degree: {cen["plain_count_matches"]}')
        # exact betweenness only on the small seller graphs
        if g.vcount() <= 4000 and g.ecount() <= 20000:
            bb = np.array(g.betweenness(weights=None))
            bc = np.array(g.betweenness(weights='weight'))
            top_b = np.argsort(-bb)[:5]
            entry['betweenness_top5_unweighted'] = [g.vs['name'][i] for i in top_b]
            entry['betweenness_weight_vs_unweighted_spearman'] = round(
                float(__import__('scipy.stats', fromlist=['spearmanr']).spearmanr(bb, bc)[0]), 4)
            kc = g.coreness()
            maxk = max(kc)
            entry['kcore_top_core_size'] = int(sum(1 for k in kc if k >= maxk))
            md.append(f'- betweenness top-5 (unweighted): {entry["betweenness_top5_unweighted"]}; '
                      f'weighted vs unweighted rho={entry["betweenness_weight_vs_unweighted_spearman"]}')
        report['results'][name] = entry
        md.append('')

    (REPORTS / 'p4_graph_algorithms.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (REPORTS / 'p4_graph_algorithms_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('p4 done:', {k: (v['nodes'], v['edges']) for k, v in report['results'].items()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
