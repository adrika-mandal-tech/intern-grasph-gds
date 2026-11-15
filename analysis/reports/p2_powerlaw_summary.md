# Phase 2 — power-law fits (source CSV)

**Source-only: NOT a verified Grasph graph export.**

Method: Clauset-Shalizi-Newman continuous power-law fit; xmin by KS; exponent by MLE; p by semi-parametric bootstrap; competitors by per-point log-likelihood-ratio (Vuong). Bootstrap reps: 300, seed 20261009.

## Fits
- **seller_item_incidence** (n=3,095, 3,095 sellers with >=1 item): tail=200, xmin=121, alpha=2.381, KS D=0.0456, p=0.590.
  - vs lognormal: R=+0.3197, p=0.000.
  - vs exponential: R=+0.6053, p=0.000.
  - concentration: top 30 of 3,095 (26.42%) account for 112,650 items.
- **product_item_incidence** (n=32,951, 32,951 products sold in >=1 item): tail=368, xmin=31, alpha=2.625, KS D=0.0358, p=0.557.
  - vs lognormal: R=+0.3435, p=0.000.
  - vs exponential: R=+0.6991, p=0.000.
  - concentration: top 329 of 32,951 (22.09%) account for 112,650 items.
- **person_order_count** (n=96,096, 96,096 unique people (customer_unique_id)): tail=252, xmin=3, alpha=12.325, KS D=0.8056, p=0.000.
  - vs lognormal: R=+1.3178, p=0.000.
  - vs exponential: R=+2.4583, p=0.000.
  - concentration: top 960 of 96,096 (2.28%) account for 99,441 items.
- **order_item_count** (n=98,666, 98,666 orders with >=1 item): tail=58, xmin=7, alpha=4.646, KS D=0.3793, p=0.000.
  - vs lognormal: R=+0.5043, p=0.000.
  - vs exponential: R=+1.3428, p=0.000.
  - concentration: top 986 of 98,666 (4.31%) account for 112,650 items.

## Limitations
- Counts are discrete; the continuous power law is an approximation.
- Item incidence is not projected graph degree.
- A large goodness-of-fit p does not prove a power law; it fails to reject it.
- Person order counts are right-censored: the window ends 2018-08.
- Lognormal/exponential fits use maximum likelihood with location fixed at 0.
