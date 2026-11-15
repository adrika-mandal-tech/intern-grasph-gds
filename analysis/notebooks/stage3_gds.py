#!/usr/bin/env python3
"""Stage 3: GDS - Centrality & Community Detection"""
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style("whitegrid")

try:
    import igraph as ig
    HAS_IGRAPH = True
except ImportError:
    HAS_IGRAPH = False

sc_df = pd.read_parquet("/tmp/sc_df.parquet")

if HAS_IGRAPH:
    sc_nodes = sorted(set(sc_df["seller_a"].tolist() + sc_df["seller_b"].tolist()))
    node_idx = {n:i for i,n in enumerate(sc_nodes)}
    edges_idx = [(node_idx[a], node_idx[b], w) for a,b,w in sc_df.itertuples(index=False)]
    g = ig.Graph(n=len(sc_nodes), edges=[(a,b) for a,b,_ in edges_idx])
    g.es["weight"] = [w for _,_,w in edges_idx]
    g.vs["name"] = sc_nodes
    print(f"Graph: {g.vcount()} nodes, {g.ecount()} edges", flush=True)

    # Centrality
    pr = g.pagerank(weights="weight")
    deg = g.degree(mode="all")
    cent_df = pd.DataFrame({"seller": sc_nodes, "pagerank": pr, "degree": deg})
    cent_df = cent_df.sort_values("pagerank", ascending=False).head(15)
    print("\nTop 15 by PageRank:", flush=True)
    print(cent_df.to_string(), flush=True)
    rho = cent_df["pagerank"].corr(cent_df["degree"], method="spearman")
    print(f"\nSpearman rho (PageRank vs Degree): {rho:.4f}", flush=True)

    # Communities
    try:
        communities = g.community_leiden(objective_function="modularity", n_iterations=10, seed=42)
        print(f"\nCommunities: {len(communities)}", flush=True)
        mod = g.modularity(communities.membership)
        print(f"Modularity: {mod:.4f}", flush=True)
        sizes = Counter(communities.membership)
        print(f"Community sizes: {dict(sorted(sizes.items(), key=lambda x:-x[1]))}", flush=True)
    except Exception as e:
        print(f"Leiden failed: {e}", flush=True)
        communities = g.community_multilevel()
        mod = g.modularity(communities.membership)
        print(f"Fallback multilevel: {len(communities)} communities, Q={mod:.4f}", flush=True)

    # Null model
    null_mods = []
    for seed in range(20):
        g_null = g.copy()
        g_null.rewire(n=100 * g_null.ecount(), mode="simple")
        comm = g_null.community_multilevel()
        null_mods.append(g_null.modularity(comm.membership))
    print(f"\nNull modularity: mean={np.mean(null_mods):.4f} std={np.std(null_mods):.4f}", flush=True)
    print(f"Observed Q={mod:.4f} → z-score={(mod - np.mean(null_mods))/np.std(null_mods):.1f}", flush=True)
else:
    print("igraph not available")
