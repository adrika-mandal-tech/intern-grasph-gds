#!/usr/bin/env python3
"""Olist x GrasPh: Graph Data Science Pipeline
Replicates task01_profile.py through task10_datascience_report.py in notebook form.
Run: analysis/.venv/bin/python analysis/notebooks/olist_pipeline.py
"""
import warnings
warnings.filterwarnings('ignore')

import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np
import pandas as pd
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
    print("igraph not installed")

try:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, average_precision_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

ROOT = Path(".").resolve()
CSV_DIR = ROOT / "Olist-Kaggle-dataset"
REPORTS = ROOT / "analysis" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

print(f"Root: {ROOT}")
print(f"CSV dir exists: {CSV_DIR.exists()}")
print(f"igraph: {HAS_IGRAPH} | sklearn: {HAS_SKLEARN}")
print()

# ============================================================
# CELL 1 — Load 9 Olist CSVs
# ============================================================
SOURCES = {
    "Order": ("olist_orders_dataset.csv", ["order_id", "customer_id", "order_status", "order_purchase_timestamp"]),
    "Customer": ("olist_customers_dataset.csv", ["customer_id", "customer_unique_id", "customer_zip_code_prefix"]),
    "OrderItem": ("olist_order_items_dataset.csv", ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"]),
    "Payment": ("olist_order_payments_dataset.csv", ["order_id", "payment_sequential", "payment_type", "payment_value"]),
    "Review": ("olist_order_reviews_dataset.csv", ["review_id", "order_id", "review_score", "review_creation_date"]),
    "Product": ("olist_products_dataset.csv", ["product_id", "product_category_name", "product_weight_g"]),
    "Seller": ("olist_sellers_dataset.csv", ["seller_id", "seller_zip_code_prefix"]),
    "ProductCategory": ("product_category_name_translation.csv", ["product_category_name", "product_category_name_english"]),
}

dfs = {}
for name, (fname, cols) in SOURCES.items():
    dfs[name] = pd.read_csv(CSV_DIR / fname)
    dfs[name] = dfs[name][[c for c in cols if c in dfs[name].columns]]
    print(f"{name:15s}: {len(dfs[name]):>7,} rows × {dfs[name].shape[1]} cols")

# ============================================================
# CELL 2 — Null rates per column
# ============================================================
null_rows = []
for name, df in dfs.items():
    for col in df.columns:
        n_null = df[col].isna().sum()
        null_rows.append({"label": name, "column": col, "nulls": int(n_null), "null_pct": round(100 * n_null / len(df), 2)})

null_df = pd.DataFrame(null_rows)
print("\nNull rates (top 15):")
print(null_df.sort_values(["label", "column"]).head(15).to_string())

# ============================================================
# CELL 3 — Key uniqueness & cardinality
# ============================================================
print("\nKey uniqueness checks:")
key_checks = [
    ("Order", "order_id"),
    ("Customer", "customer_id"),
    ("OrderItem", "order_id"),
    ("Review", "review_id"),
    ("Product", "product_id"),
    ("Seller", "seller_id"),
]
for label, key in key_checks:
    n = len(dfs[label])
    n_unique = dfs[label][key].nunique()
    print(f"  {label:15s} {key:25s}: rows={n:>7,} unique={n_unique:>7,} duplicates={n - n_unique:>7,}")

order_customer = dfs["Order"].merge(dfs["Customer"], on="customer_id", how="left")
n_orders = len(dfs["Order"])
n_people = order_customer["customer_unique_id"].nunique()
orders_per_person = order_customer.groupby("customer_unique_id").size()
n_repeat = (orders_per_person > 1).sum()
print(f"\nOrders: {n_orders:,} | Unique people: {n_people:,} | Repeat buyers: {n_repeat:,} ({100*n_repeat/n_people:.1f}%)")

# ============================================================
# CELL 4 — Build flat analysis table
# ============================================================
flat = dfs["OrderItem"].merge(
    dfs["Order"][['order_id','order_purchase_timestamp','order_status','customer_id']],
    on="order_id", how="left"
)
flat = flat.merge(
    dfs["Customer"][['customer_id','customer_unique_id','customer_zip_code_prefix']],
    on="customer_id", how="left"
)
flat = flat.merge(
    dfs["Product"][['product_id','product_category_name','product_weight_g']],
    on="product_id", how="left"
)
flat = flat.merge(
    dfs["Seller"][['seller_id','seller_zip_code_prefix']],
    on="seller_id", how="left"
)
print(f"\nFlat table: {flat.shape[0]:,} rows × {flat.shape[1]} cols")

# ============================================================
# CELL 5 — Co-occurrence edge builder
# ============================================================
def co_occur_edges(df, entity_col, attr_col):
    attr_to_entities = defaultdict(set)
    for _, row in df.iterrows():
        attr_to_entities[row[attr_col]].add(row[entity_col])
    edges = Counter()
    for ents in attr_to_entities.values():
        ents = sorted(ents)
        for i in range(len(ents)):
            for j in range(i+1, len(ents)):
                edges[(ents[i], ents[j])] += 1
    return edges

# ============================================================
# CELL 6 — Projection: seller_shared_categories
# ============================================================
sc_edges = co_occur_edges(flat, "seller_id", "product_category_name")
sc_df = pd.DataFrame([(a,b,w) for (a,b),w in sc_edges.items()], columns=["seller_a","seller_b","weight"])
print(f"\nseller_shared_categories: {len(sc_edges):,} edges")
print(sc_df["weight"].describe().to_string())

# ============================================================
# CELL 7 — Projection: seller_shared_products
# ============================================================
sp_edges = co_occur_edges(flat, "seller_id", "product_id")
sp_df = pd.DataFrame([(a,b,w) for (a,b),w in sp_edges.items()], columns=["seller_a","seller_b","weight"])
print(f"\nseller_shared_products: {len(sp_df):,} edges")
print(sp_df["weight"].describe().to_string())

# ============================================================
# CELL 8 — Projection: product_bought_together
# ============================================================
pb_edges = co_occur_edges(flat, "product_id", "order_id")
pb_df = pd.DataFrame([(a,b,w) for (a,b),w in pb_edges.items()], columns=["product_a","product_b","weight"])
print(f"\nproduct_bought_together: {len(pb_df):,} edges")
print(pb_df["weight"].describe().to_string())

# ============================================================
# CELL 9 — Projection: seller_co_order
# ============================================================
co_edges = co_occur_edges(flat, "seller_id", "order_id")
co_df = pd.DataFrame([(a,b,w) for (a,b),w in co_edges.items()], columns=["seller_a","seller_b","weight"])
print(f"\nseller_co_order: {len(co_df):,} edges")

# ============================================================
# CELL 10 — Build igraph from seller_shared_categories
# ============================================================
mod = None
g = None
if HAS_IGRAPH:
    sc_nodes = sorted(set(sc_df["seller_a"].tolist() + sc_df["seller_b"].tolist()))
    node_idx = {n:i for i,n in enumerate(sc_nodes)}
    edges_idx = [(node_idx[a], node_idx[b], w) for a,b,w in sc_df.itertuples(index=False)]
    g = ig.Graph(n=len(sc_nodes), edges=[(a,b) for a,b,_ in edges_idx])
    g.es["weight"] = [w for _,_,w in edges_idx]
    g.vs["name"] = sc_nodes
    print(f"\nGraph: {g.vcount()} nodes, {g.ecount()} edges")
else:
    print("\nigraph not available — skipping GDS")

# ============================================================
# CELL 11 — Centrality: PageRank vs Degree
# ============================================================
if HAS_IGRAPH:
    pr = g.pagerank(weights="weight")
    deg = g.degree(mode="all")
    cent_df = pd.DataFrame({"seller": sc_nodes, "pagerank": pr, "degree": deg})
    cent_df = cent_df.sort_values("pagerank", ascending=False).head(15)
    print("\nTop 15 by PageRank:")
    print(cent_df.to_string())
    rho = cent_df["pagerank"].corr(cent_df["degree"], method="spearman")
    print(f"\nSpearman rho (PageRank vs Degree): {rho:.4f}")

    fig, ax = plt.subplots(1,2, figsize=(14,5))
    sns.scatterplot(data=cent_df, x="degree", y="pagerank", ax=ax[0], alpha=0.6)
    ax[0].set_title("PageRank vs Degree")
    sns.histplot(cent_df["pagerank"], bins=30, kde=True, ax=ax[1], color="purple")
    ax[1].set_title("PageRank Distribution")
    plt.tight_layout()
    plt.savefig("/tmp/pagerank.png", dpi=100)
    plt.close()
    print("Saved /tmp/pagerank.png")

# ============================================================
# CELL 12 — Community Detection: Leiden / Louvain
# ============================================================
if HAS_IGRAPH:
    try:
        communities = g.community_leiden(objective_function="modularity", n_iterations=10, seed=42)
        print(f"\nCommunities: {len(communities)}")
        mod = g.modularity(communities.membership)
        print(f"Modularity: {mod:.4f}")
        sizes = Counter(communities.membership)
        print(f"Community sizes: {dict(sorted(sizes.items(), key=lambda x:-x[1]))}")
    except Exception as e:
        print(f"Leiden failed: {e}")
        communities = g.community_multilevel()
        mod = g.modularity(communities.membership)
        print(f"Fallback multilevel: {len(communities)} communities, Q={mod:.4f}")

# ============================================================
# CELL 13 — Null model: degree-preserving rewiring
# ============================================================
if HAS_IGRAPH:
    null_mods = []
    for seed in range(20):
        g_null = g.copy()
        g_null.rewire(n=100 * g_null.ecount(), mode="simple")
        comm = g_null.community_multilevel()
        null_mods.append(g_null.modularity(comm.membership))
    print(f"\nNull modularity: mean={np.mean(null_mods):.4f} std={np.std(null_mods):.4f}")
    print(f"Observed Q={mod:.4f} → z-score={(mod - np.mean(null_mods))/np.std(null_mods):.1f}")
    sns.histplot(null_mods, bins=20, kde=True, color="gray")
    plt.axvline(mod, color="purple", linestyle="--", label=f"Observed Q={mod:.3f}")
    plt.legend()
    plt.title("Null Modularity Distribution")
    plt.tight_layout()
    plt.savefig("/tmp/null_modularity.png", dpi=100)
    plt.close()
    print("Saved /tmp/null_modularity.png")

# ============================================================
# CELL 14 — Temporal split for link prediction
# ============================================================
flat["order_purchase_timestamp"] = pd.to_datetime(flat["order_purchase_timestamp"], errors="coerce")
cutoff = "2018-06-01"
train_items = flat[flat["order_purchase_timestamp"] < cutoff]
test_items = flat[flat["order_purchase_timestamp"] >= cutoff]
print(f"\nTrain orders: {train_items['order_id'].nunique():,} | Test orders: {test_items['order_id'].nunique():,}")

# ============================================================
# CELL 15 — Build train/test seller projections
# ============================================================
train_sc = co_occur_edges(train_items, "seller_id", "product_category_name")
test_sc = co_occur_edges(test_items, "seller_id", "product_category_name")
train_sellers = set()
for (a,b) in train_sc:
    train_sellers.add(a); train_sellers.add(b)

# ============================================================
# CELL 16 — Adamic-Adar & Common Neighbors
# ============================================================
def adamic_adar(a, b, graph_edges):
    nbrs = defaultdict(set)
    for (x,y) in graph_edges:
        nbrs[x].add(y); nbrs[y].add(x)
    shared = nbrs.get(a, set()) & nbrs.get(b, set())
    if not shared: return 0.0
    deg = {n: len(nbrs[n]) for n in shared}
    return sum(1.0 / np.log(d) for d in deg.values() if d > 1)

def common_neighbors(a, b, graph_edges):
    nbrs = defaultdict(set)
    for (x,y) in graph_edges:
        nbrs[x].add(y); nbrs[y].add(x)
    return len(nbrs.get(a, set()) & nbrs.get(b, set()))

# ============================================================
# CELL 17 — Evaluate link prediction (AUC)
# ============================================================
train_set = set(train_sc.keys())
test_set = set(test_sc.keys())
pos_pairs = list(test_set - train_set)
print(f"\nPositive test pairs: {len(pos_pairs):,}")

all_sellers = list(train_sellers)
neg_pairs = set()
while len(neg_pairs) < len(pos_pairs):
    a, b = np.random.choice(all_sellers, 2, replace=False)
    pair = tuple(sorted((a,b)))
    if pair not in train_set and pair not in test_set:
        neg_pairs.add(pair)

neg_pairs = list(neg_pairs)
scores = []
for a,b in pos_pairs + neg_pairs:
    scores.append({
        "pair": (a,b),
        "label": 1 if (a,b) in pos_pairs else 0,
        "adamic_adar": adamic_adar(a,b,train_sc),
        "common_neighbors": common_neighbors(a,b,train_sc)
    })

score_df = pd.DataFrame(scores)
score_df["label"] = score_df["label"].astype(int)
auc_aa = roc_auc_score(score_df["label"], score_df["adamic_adar"])
auc_cn = roc_auc_score(score_df["label"], score_df["common_neighbors"])
print(f"Adamic-Adar AUC: {auc_aa:.4f}")
print(f"Common Neighbors AUC: {auc_cn:.4f}")

# ============================================================
# CELL 18 — Build ML feature table
# ============================================================
ml = flat.dropna(subset=["order_purchase_timestamp", "price", "freight_value", "product_weight_g"]).copy()
ml["delivery_late"] = (ml["order_status"] == "delivered").astype(int)
features = ["price", "freight_value", "product_weight_g"]
X = ml[features].fillna(ml[features].median())
y = ml["delivery_late"]
print(f"\nML table: {X.shape[0]:,} rows × {X.shape[1]} features | Positive rate: {y.mean():.3f}")

# ============================================================
# CELL 19 — Train HistGradientBoosting
# ============================================================
auc = None
if HAS_SKLEARN:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    clf = HistGradientBoostingClassifier(random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred)
    ap = average_precision_score(y_test, y_pred)
    print(f"\nAUC: {auc:.4f} | Average Precision: {ap:.4f} | Prevalence: {y_test.mean():.3f}")
    imp = pd.DataFrame({"feature": features, "importance": clf.feature_importances_})
    print(imp.sort_values("importance", ascending=False).to_string())

# ============================================================
# CELL 20 — Gini coefficient (Lorenz curve)
# ============================================================
seller_rev = flat.groupby("seller_id")["price"].sum().sort_values()

def gini(x):
    x = np.sort(np.array(x))
    n = len(x)
    return (np.sum((2 * np.arange(1, n+1) - n - 1) * x)) / (n * np.sum(x))

g = gini(seller_rev.values)
print(f"\nRevenue Gini: {g:.4f}")
print(f"Top 1% sellers revenue share: {seller_rev.tail(int(len(seller_rev)*0.01)).sum() / seller_rev.sum():.3f}")

sns.lineplot(x=np.arange(len(seller_rev)), y=np.cumsum(seller_rev.values) / seller_rev.values.sum())
plt.plot([0, len(seller_rev)], [0, 1], "r--", label="equality")
plt.xlabel("Sellers (poorest→richest)")
plt.ylabel("Cumulative revenue share")
plt.title(f"Lorenz Curve — Gini = {g:.3f}")
plt.legend()
plt.tight_layout()
plt.savefig("/tmp/lorenz.png", dpi=100)
plt.close()
print("Saved /tmp/lorenz.png")

# ============================================================
# CELL 21 — Power-law fit on seller item-incidence
# ============================================================
seller_items = flat.groupby("seller_id")["product_id"].nunique()
x = seller_items.values
x = x[x > 0]
xmin = x.min()
alpha = 1 + len(x) / np.sum(np.log(x / xmin))
print(f"\nSeller item-incidence power law: alpha = {alpha:.3f}, xmin = {xmin}")

# ============================================================
# CELL 22 — Export results
# ============================================================
results = {
    "gini": float(g),
    "modularity": float(mod) if HAS_IGRAPH else None,
    "aa_auc": float(auc_aa) if "auc_aa" in dir() else None,
    "ml_auc": float(auc) if HAS_SKLEARN else None,
    "powerlaw_alpha": float(alpha)
}

with open(REPORTS / "notebook_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nSaved: {REPORTS / 'notebook_results.json'}")
print(json.dumps(results, indent=2))
print("\nPipeline complete.")
