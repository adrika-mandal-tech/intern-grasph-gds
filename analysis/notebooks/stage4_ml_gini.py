#!/usr/bin/env python3
"""Stage 4: Link Prediction + ML + Gini"""
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
import json
from pathlib import Path
from collections import defaultdict, Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style("whitegrid")

try:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, average_precision_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

ROOT = Path(".").resolve()
flat = pd.read_parquet("/tmp/flat.parquet")
sc_df = pd.read_parquet("/tmp/sc_df.parquet")

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
# Link Prediction
# ============================================================
flat["order_purchase_timestamp"] = pd.to_datetime(flat["order_purchase_timestamp"], errors="coerce")
cutoff = "2018-06-01"
train_items = flat[flat["order_purchase_timestamp"] < cutoff]
test_items = flat[flat["order_purchase_timestamp"] >= cutoff]
print(f"Train orders: {train_items['order_id'].nunique():,} | Test orders: {test_items['order_id'].nunique():,}", flush=True)

train_sc = co_occur_edges(train_items, "seller_id", "product_category_name")
test_sc = co_occur_edges(test_items, "seller_id", "product_category_name")
train_sellers = set()
for (a,b) in train_sc:
    train_sellers.add(a); train_sellers.add(b)

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

train_set = set(train_sc.keys())
test_set = set(test_sc.keys())
pos_pairs = list(test_set - train_set)
print(f"Positive test pairs: {len(pos_pairs):,}", flush=True)

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
print(f"Adamic-Adar AUC: {auc_aa:.4f}", flush=True)
print(f"Common Neighbors AUC: {auc_cn:.4f}", flush=True)

# ============================================================
# ML - Late Delivery
# ============================================================
ml = flat.dropna(subset=["order_purchase_timestamp", "price", "freight_value", "product_weight_g"]).copy()
ml["delivery_late"] = (ml["order_status"] == "delivered").astype(int)
features = ["price", "freight_value", "product_weight_g"]
X = ml[features].fillna(ml[features].median())
y = ml["delivery_late"]
print(f"\nML table: {X.shape[0]:,} rows × {X.shape[1]} features | Positive rate: {y.mean():.3f}", flush=True)

auc = None
if HAS_SKLEARN:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    clf = HistGradientBoostingClassifier(random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred)
    ap = average_precision_score(y_test, y_pred)
    print(f"AUC: {auc:.4f} | Average Precision: {ap:.4f} | Prevalence: {y_test.mean():.3f}", flush=True)
    imp = pd.DataFrame({"feature": features, "importance": clf.feature_importances_})
    print(imp.sort_values("importance", ascending=False).to_string(), flush=True)

# ============================================================
# Gini coefficient
# ============================================================
seller_rev = flat.groupby("seller_id")["price"].sum().sort_values()

def gini(x):
    x = np.sort(np.array(x))
    n = len(x)
    return (np.sum((2 * np.arange(1, n+1) - n - 1) * x)) / (n * np.sum(x))

g = gini(seller_rev.values)
print(f"\nRevenue Gini: {g:.4f}", flush=True)
print(f"Top 1% sellers revenue share: {seller_rev.tail(int(len(seller_rev)*0.01)).sum() / seller_rev.sum():.3f}", flush=True)

# ============================================================
# Power-law fit
# ============================================================
seller_items = flat.groupby("seller_id")["product_id"].nunique()
x = seller_items.values
x = x[x > 0]
xmin = x.min()
alpha = 1 + len(x) / np.sum(np.log(x / xmin))
print(f"\nSeller item-incidence power law: alpha = {alpha:.3f}, xmin = {xmin}", flush=True)

# ============================================================
# Export
# ============================================================
REPORTS = ROOT / "analysis" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)
results = {
    "gini": float(g),
    "aa_auc": float(auc_aa),
    "ml_auc": float(auc) if HAS_SKLEARN else None,
    "powerlaw_alpha": float(alpha)
}
with open(REPORTS / "notebook_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved: {REPORTS / 'notebook_results.json'}", flush=True)
print(json.dumps(results, indent=2), flush=True)
print("\nPipeline complete!", flush=True)
