# Phase 3 — source-derived projections

**Derived from the raw local CSVs, NOT a verified Grasph export.**

Date window: 2016-09 to 2018-10. Dense cliques expand only below 3,000,000 edges; otherwise membership groups are stored.

| projection | nodes | edges | candidate pairs (est.) | weight |
| --- | ---: | ---: | ---: | --- |
| seller_shared_products | 3095 | 1061 | 1897 | # distinct products sold by both sellers |
| seller_shared_categories | 3095 | 724613 | 821642 | # distinct categories both sellers sell |
| seller_co_order | 3095 | 1151 | 1419 | # orders containing both sellers |
| product_bought_together | 32951 | 4058 | 4481 | # orders containing both products (repeated units not counted twice) |
| category_shared_sellers | 74 | 1435 | 10690 | # sellers selling in both categories |
| product_same_category | 32951 | 0 | 26829566 | # products in the same category (clique) |
| product_same_seller | 32951 | 1097660 | 1101043 | # products sold by the same seller (clique) |
| order_product_incidence |  | 102425 |  | units and summed item price |
| person_projection | 95420 |  |  | orders per person; products/sellers are distinct membership |

## Limitations
- Source-derived; graph retention of duplicate review/zip keys is unverified.
- Candidate pair counts are exact from source membership, not graph degree.
