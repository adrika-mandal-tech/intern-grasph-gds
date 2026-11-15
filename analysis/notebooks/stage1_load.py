#!/usr/bin/env python3
"""Stage 1: Load data and build flat table"""
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
from pathlib import Path

ROOT = Path(".").resolve()
CSV_DIR = ROOT / "Olist-Kaggle-dataset"

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
    print(f"{name:15s}: {len(dfs[name]):>7,} rows × {dfs[name].shape[1]} cols", flush=True)

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
print(f"\nFlat table: {flat.shape[0]:,} rows × {flat.shape[1]} cols", flush=True)

# Save flat table for reuse
flat.to_parquet("/tmp/flat.parquet")
print("Saved /tmp/flat.parquet", flush=True)
