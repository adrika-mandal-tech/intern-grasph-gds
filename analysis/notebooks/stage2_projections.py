#!/usr/bin/env python3
"""Stage 2: Build graph projections"""
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(".").resolve()
flat = pd.read_parquet("/tmp/flat.parquet")
print(f"Flat table: {flat.shape}", flush=True)

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

# seller_shared_categories
sc_edges = co_occur_edges(flat, "seller_id", "product_category_name")
sc_df = pd.DataFrame([(a,b,w) for (a,b),w in sc_edges.items()], columns=["seller_a","seller_b","weight"])
print(f"seller_shared_categories: {len(sc_edges):,} edges", flush=True)

# seller_shared_products
sp_edges = co_occur_edges(flat, "seller_id", "product_id")
sp_df = pd.DataFrame([(a,b,w) for (a,b),w in sp_edges.items()], columns=["seller_a","seller_b","weight"])
print(f"seller_shared_products: {len(sp_df):,} edges", flush=True)

# product_bought_together
pb_edges = co_occur_edges(flat, "product_id", "order_id")
pb_df = pd.DataFrame([(a,b,w) for (a,b),w in pb_edges.items()], columns=["product_a","product_b","weight"])
print(f"product_bought_together: {len(pb_df):,} edges", flush=True)

# seller_co_order
co_edges = co_occur_edges(flat, "seller_id", "order_id")
co_df = pd.DataFrame([(a,b,w) for (a,b),w in co_edges.items()], columns=["seller_a","seller_b","weight"])
print(f"seller_co_order: {len(co_df):,} edges", flush=True)

sc_df.to_parquet("/tmp/sc_df.parquet")
sp_df.to_parquet("/tmp/sp_df.parquet")
pb_df.to_parquet("/tmp/pb_df.parquet")
co_df.to_parquet("/tmp/co_df.parquet")
print("Saved all projections to /tmp/", flush=True)
