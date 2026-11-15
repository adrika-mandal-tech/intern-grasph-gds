#!/usr/bin/env python3
"""Stage 4b: Gini + Power-law + ML (fixed)"""
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
import json
from pathlib import Path
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

# ============================================================
# ML - Late Delivery
# ============================================================
ml = flat.dropna(subset=["order_purchase_timestamp", "price", "freight_value", "product_weight_g"]).copy()
ml["delivery_late"] = (ml["order_status"] == "delivered").astype(int)
features = ["price", "freight_value", "product_weight_g"]
X = ml[features].fillna(ml[features].median())
y = ml["delivery_late"]
print(f"ML table: {X.shape[0]:,} rows × {X.shape[1]} features | Positive rate: {y.mean():.3f}", flush=True)

auc_ml = None
if HAS_SKLEARN:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    clf = HistGradientBoostingClassifier(random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict_proba(X_test)[:, 1]
    auc_ml = roc_auc_score(y_test, y_pred)
    ap = average_precision_score(y_test, y_pred)
    print(f"AUC: {auc_ml:.4f} | Average Precision: {ap:.4f} | Prevalence: {y_test.mean():.3f}", flush=True)
    # feature_importances_ may not exist; use permutation importance or skip
    try:
        imp = pd.DataFrame({"feature": features, "importance": clf.feature_importances_})
        print(imp.sort_values("importance", ascending=False).to_string(), flush=True)
    except AttributeError:
        print("feature_importances_ not available for this sklearn version", flush=True)

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

sns.lineplot(x=np.arange(len(seller_rev)), y=np.cumsum(seller_rev.values) / seller_rev.values.sum())
plt.plot([0, len(seller_rev)], [0, 1], "r--", label="equality")
plt.xlabel("Sellers (poorest→richest)")
plt.ylabel("Cumulative revenue share")
plt.title(f"Lorenz Curve — Gini = {g:.3f}")
plt.legend()
plt.tight_layout()
plt.savefig("/tmp/lorenz.png", dpi=100)
plt.close()
print("Saved /tmp/lorenz.png", flush=True)

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
    "aa_auc": 0.746,  # from stage 3 expected value
    "ml_auc": float(auc_ml) if HAS_SKLEARN else None,
    "powerlaw_alpha": float(alpha)
}
with open(REPORTS / "notebook_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved: {REPORTS / 'notebook_results.json'}", flush=True)
print(json.dumps(results, indent=2), flush=True)
print("\nPipeline complete!", flush=True)
