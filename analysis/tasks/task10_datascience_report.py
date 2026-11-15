#!/usr/bin/env python3
"""Task 10 - compute the exact numbers embedded in Datascience.html.

Read-only: consumes the source CSVs (verified 0-diff to the GrasPh graph per
TASK 11.5/11.6 of the field manual). Every figure this script emits is written
to reports/datascience/metrics.json and is reproducible from the CSVs alone.

Deps: pandas + numpy only.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/adrikamandal/Desktop/GEN AI/PrajnaAI/intern-grasph-gds")
DATA = ROOT / "Olist-Kaggle-dataset"
OUT = ROOT / "reports" / "datascience"


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    sx = x - x.mean()
    sy = y - y.mean()
    den = np.sqrt((sx * sx).sum() * (sy * sy).sum())
    return float((sx * sy).sum() / den) if den else 0.0


def gini(vals: np.ndarray) -> float:
    x = np.sort(vals)
    n = x.size
    cum = np.cumsum(x)
    if cum[-1] == 0:
        return 0.0
    lorenz = np.concatenate([[0.0], cum / cum[-1]])
    lorenz_x = np.linspace(0.0, 1.0, n + 1)
    area = np.trapezoid(lorenz, lorenz_x)
    return float(1.0 - 2.0 * area)


def lorenz_curve(vals: np.ndarray, points: int = 20) -> list:
    x = np.sort(vals)
    n = x.size
    cum = np.cumsum(x)
    if cum[-1] == 0:
        return [[0.0, 0.0], [1.0, 1.0]]
    curve = []
    for i in range(points + 1):
        p = i / points
        idx = min(max(int(round(p * n)), 0), n)
        share = cum[idx - 1] / cum[-1] if idx > 0 else 0.0
        curve.append([round(p, 3), round(float(share), 4)])
    return curve



def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    items = read("olist_order_items_dataset.csv")
    orders = read("olist_orders_dataset.csv")
    reviews = read("olist_order_reviews_dataset.csv")
    sellers = read("olist_sellers_dataset.csv")
    products = read("olist_products_dataset.csv")
    translation = read("product_category_name_translation.csv")

    base = items.merge(
        orders[
            [
                "order_id",
                "order_status",
                "order_purchase_timestamp",
                "order_delivered_carrier_date",
                "order_delivered_customer_date",
                "order_estimated_delivery_date",
            ]
        ],
        on="order_id",
        how="left",
    )
    reviews_dedup = reviews.drop_duplicates("review_id")
    base = base.merge(
        reviews_dedup[["review_id", "order_id", "review_score"]],
        on="order_id",
        how="left",
    )

    seller_rev = base.groupby("seller_id")["price"].sum().sort_values(ascending=False)
    n_sellers = len(seller_rev)
    top_share = {
        "top_1pct": round(float(seller_rev.head(max(1, n_sellers // 100)).sum() / seller_rev.sum() * 100), 2),
        "top_5pct": round(float(seller_rev.head(max(1, n_sellers // 20)).sum() / seller_rev.sum() * 100), 2),
        "top_10pct": round(float(seller_rev.head(max(1, n_sellers // 10)).sum() / seller_rev.sum() * 100), 2),
        "top_30": round(float(seller_rev.head(30).sum() / seller_rev.sum() * 100), 2),
    }
    item_counts = base.groupby("seller_id").size()
    half_sellers = int(item_counts.sort_values(ascending=False).cumsum().searchsorted(len(base) / 2) + 1)
    revenue_gini = gini(seller_rev.values)
    item_gini = gini(item_counts.values.astype(float))

    base["delivered_customer_date"] = pd.to_datetime(base["order_delivered_customer_date"], errors="coerce")
    base["estimated_delivery_date"] = pd.to_datetime(base["order_estimated_delivery_date"], errors="coerce")
    base["review_score"] = pd.to_numeric(base["review_score"], errors="coerce")
    base["is_late"] = (base["delivered_customer_date"] > base["estimated_delivery_date"]) & base[
        "delivered_customer_date"
    ].notna()

    has_review = base[base["review_score"].notna()].copy()
    has_review["is_late"] = has_review["is_late"].fillna(False)
    late_scores = has_review.loc[has_review["is_late"], "review_score"]
    ontime_scores = has_review.loc[~has_review["is_late"], "review_score"]
    delay_days = (has_review["delivered_customer_date"] - has_review["estimated_delivery_date"]).dt.days.fillna(0)
    delay_review_r = pearson(delay_days.values, has_review["review_score"].values.astype(float))

    review_delay = {
        "n_with_review": int(len(has_review)),
        "n_late": int(has_review["is_late"].sum()),
        "n_ontime": int((~has_review["is_late"]).sum()),
        "late_share_pct": round(float(has_review["is_late"].mean() * 100), 2),
        "mean_late_score": round(float(late_scores.mean()), 3),
        "mean_ontime_score": round(float(ontime_scores.mean()), 3),
        "pearson_delay_score": round(delay_review_r, 3),
    }

    buckets = []
    edges = [-np.inf, 0, 3, 7, 14, np.inf]
    labels = ["On time", "1-3 days late", "4-7 days late", "8-14 days late", "15+ days late"]
    has_review["bucket"] = pd.cut(
        (has_review["delivered_customer_date"] - has_review["estimated_delivery_date"]).dt.days,
        bins=edges,
        labels=labels,
    )
    for lb in labels:
        grp = has_review[has_review["bucket"] == lb]
        buckets.append(
            {
                "bucket": lb,
                "n": int(len(grp)),
                "mean_review": round(float(grp["review_score"].mean()), 3),
                "low_review_pct": round(float((grp["review_score"] <= 2).mean() * 100), 1),
            }
        )


    seller_state = sellers[["seller_id", "seller_state"]].drop_duplicates("seller_id")
    with_state = base.merge(seller_state, on="seller_id", how="left")
    state_stats = with_state.groupby("seller_state").agg(
        n_items=("price", "size"),
        n_orders=("order_id", "nunique"),
        n_late=("is_late", "sum"),
        mean_price=("price", "mean"),
    )
    state_stats["late_pct"] = (state_stats["n_late"] / state_stats["n_items"] * 100).round(2)
    state_stats["mean_price"] = state_stats["mean_price"].round(2)
    top_states = state_stats.sort_values("n_items", ascending=False).head(8).reset_index()

    seller_scores = (
        has_review.groupby("seller_id")["review_score"].agg(["mean", "size"]).reset_index()
    )
    seller_scores.columns = ["seller_id", "mean_score", "n_reviews"]
    seller_late = with_state.groupby("seller_id")["is_late"].mean().rename("late_rate")
    seller_quality = (
        seller_scores.merge(seller_late, on="seller_id", how="left")
        .merge(seller_state, on="seller_id", how="left")
        .merge(item_counts.rename("items_sold").reset_index(), on="seller_id", how="left")
    )
    seller_quality["late_rate"] = (seller_quality["late_rate"] * 100).round(2)
    seller_quality["mean_score"] = seller_quality["mean_score"].round(3)
    seller_quality = seller_quality[seller_quality["n_reviews"] >= 20]
    seller_quality["risk_flag"] = (
        (seller_quality["late_rate"] >= 15) | (seller_quality["mean_score"] <= 3.5)
    ).astype(int)
    top_risk_sellers = (
        seller_quality[seller_quality["risk_flag"] == 1]
        .sort_values("late_rate", ascending=False)
        .head(10)[["seller_id", "seller_state", "n_reviews", "mean_score", "late_rate"]]
    )

    prod_cat = products[["product_id", "product_category_name"]].merge(
        translation[["product_category_name", "product_category_name_english"]],
        on="product_category_name",
        how="left",
    )
    items_cat = items.merge(prod_cat, on="product_id", how="left")
    items_cat["category_en"] = items_cat["product_category_name_english"].fillna("(missing)")

    def _hhi(g: pd.DataFrame) -> float:
        total = g["price"].sum()
        if total <= 0:
            return 0.0
        shares = g.groupby("seller_id")["price"].sum() / total
        return float((shares ** 2).sum())

    cat_stats = (
        items_cat.groupby("category_en")
        .agg(
            n_items=("price", "size"),
            revenue=("price", "sum"),
            n_sellers=("seller_id", "nunique"),
            n_products=("product_id", "nunique"),
        )
        .reset_index()
    )
    cat_stats["revenue"] = cat_stats["revenue"].round(2)
    cat_hhi = items_cat.groupby("category_en").apply(_hhi, include_groups=False)
    cat_stats["hhi"] = cat_stats["category_en"].map(cat_hhi).round(4)
    cat_stats = cat_stats.sort_values("revenue", ascending=False)
    top_categories = cat_stats.head(15).to_dict(orient="records")
    risky_cats = cat_stats[cat_stats["n_sellers"] <= 50].sort_values("hhi", ascending=False).head(10)

    state_revenue = with_state.groupby("seller_state")["price"].sum()
    top_state_rev_share = round(float(state_revenue.head(1).sum() / state_revenue.sum() * 100), 1)

    metrics = {
        "provenance": {
            "source": "Olist-Kaggle-dataset CSVs (verified 0-diff to GrasPh graph per TASK 11.5/11.6)",
            "n_sellers": n_sellers,
            "n_items": int(len(base)),
            "revenue_brl": round(float(base["price"].sum()), 2),
            "freight_brl": round(float(base["freight_value"].sum()), 2),
        },
        "concentration": {
            "top_share": top_share,
            "half_sellers_count": half_sellers,
            "revenue_gini": round(revenue_gini, 4),
            "item_gini": round(item_gini, 4),
            "lorenz_revenue": lorenz_curve(seller_rev.values),
        },
        "review_delay": review_delay,
        "delay_buckets": buckets,
        "top_states": top_states.to_dict(orient="records"),
        "top_state_revenue_share_pct": top_state_rev_share,
        "seller_risk": {
            "n_flagged": int(seller_quality["risk_flag"].sum()),
            "n_total_with_reviews": int(len(seller_quality)),
            "top_risk": top_risk_sellers.to_dict(orient="records"),
        },
        "categories": {
            "top_by_revenue": top_categories,
            "risky_by_hhi": risky_cats[["category_en", "n_sellers", "revenue", "hhi"]].to_dict(
                orient="records"
            ),
        },
    }

    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("Written:", OUT / "metrics.json")
    print("Seller concentration:", top_share)
    print("Review vs delay:", review_delay)
    print("Category HHI top:", cat_hhi.sort_values(ascending=False).head(5).to_dict())
    print(
        "Risky categories:",
        risky_cats[["category_en", "n_sellers", "hhi"]].head().to_dict(orient="records"),
    )
    print("Seller risk count:", int(seller_quality["risk_flag"].sum()), "of", len(seller_quality))


if __name__ == "__main__":
    main()
