# Phase 2 — source CSV profiling

**Source-only results: NOT yet cross-checked against a live Grasph export.**

Checks: 41; failures: 0.

## Integrity and manual checks
- [x] Order source rows: 99441 (expected 99441)
- [x] Order duplicate primary keys: 0 (expected 0)
- [x] Customer source rows: 99441 (expected 99441)
- [x] Customer duplicate primary keys: 0 (expected 0)
- [x] OrderItem source rows: 112650 (expected 112650)
- [x] OrderItem duplicate primary keys: 0 (expected 0)
- [x] Payment source rows: 103886 (expected 103886)
- [x] Payment duplicate primary keys: 0 (expected 0)
- [x] Review source rows: 99224 (expected 99224)
- [x] Product source rows: 32951 (expected 32951)
- [x] Product duplicate primary keys: 0 (expected 0)
- [x] Seller source rows: 3095 (expected 3095)
- [x] Seller duplicate primary keys: 0 (expected 0)
- [x] Geolocation source rows: 1000163 (expected 1000163)
- [x] ProductCategory source rows: 71 (expected 71)
- [x] ProductCategory duplicate primary keys: 0 (expected 0)
- [x] Order.customer_id orphan rows: 0 (expected 0)
- [x] OrderItem.order_id orphan rows: 0 (expected 0)
- [x] OrderItem.product_id orphan rows: 0 (expected 0)
- [x] OrderItem.seller_id orphan rows: 0 (expected 0)
- [x] Payment.order_id orphan rows: 0 (expected 0)
- [x] Review.order_id orphan rows: 0 (expected 0)
- [x] unique people: 96096 (expected 96096)
- [x] repeat people: 2997 (expected 2997)
- [x] unique zip areas: 19015 (expected 19015)
- [x] Customer unmatched zip rows: 278 (expected 278)
- [x] Seller unmatched zip rows: 7 (expected 7)
- [x] products with empty category: 610 (expected 610)
- [x] products without category node: 623 (expected 623)
- [x] orders without items: 775 (expected 775)
- [x] orders without payments: 1 (expected 1)
- [x] source orders without review: 768 (expected 768)
- [x] unique review IDs: 98410 (expected 98410)
- [x] orders with exactly one item: 88863 (expected 88863)
- [x] multi-distinct-product orders: 3236 (expected 3236)
- [x] multi-seller orders: 1278 (expected 1278)
- [x] products with multiple sellers: 1225 (expected 1225)
- [x] item price total BRL: 13591643.70 (expected 13591643.70)
- [x] item freight total BRL: 2251909.54 (expected 2251909.54)
- [x] payment total BRL: 16008872.12 (expected 16008872.12)
- [x] orders missing delivery date: 2965 (expected 2965)

## First measured findings
- Repeat people: 2,997/96,096 (3.12%).
- Multi-item orders: 9,803; multi-distinct-product baskets: 3,236/99,441.
- Top 30 sellers (floor 1% of 3,095) sold 29,766/112,650 items (26.42%).
- Median observed delivery: 10.22 days (n=96,476).

## Review counts — retention sensitivity
Manual empty counts imply 40,641 non-empty messages and 11,517 titles on graph nodes, not 57,769 messages/12,531 titles. Source and first/last dedup are measured below; neither retention is assumed to match the graph.
- source_rows: {"rows": 99224, "orders_without_review": 768, "orders_with_multiple_reviews": 547, "nonempty_messages": 40950, "nonempty_titles": 11566}
- first_row_per_id: {"rows": 98410, "orders_without_review": 1274, "orders_with_multiple_reviews": 243, "nonempty_messages": 40641, "nonempty_titles": 11517}
- last_row_per_id: {"rows": 98410, "orders_without_review": 1313, "orders_with_multiple_reviews": 281, "nonempty_messages": 40641, "nonempty_titles": 11517}

## Outputs
- `p2_profile.json`: provenance hashes, checks, histograms, category concentration and temporal summaries.
- `p2_null_rates.csv`: every source column with denominator, missing/empty counts and rates.

## Limitations
- Nulls are CSV empty strings/missing fields, not graph property nulls.
- Item degree is an incidence count, not projected seller degree.
- No power-law fit or causal inference has been performed.
- Duplicate-row retention is unknown until verified against graph cache.
- Estimated delivery dates are midnight: timestamp lateness differs from calendar-day lateness.
- Connectivity, assortativity and graph-derived profiling await projections.
