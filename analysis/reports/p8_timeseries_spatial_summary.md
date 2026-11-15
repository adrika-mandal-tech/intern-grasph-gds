# Phase 8 — time series & shipping economics (haversine, proof p09)

Trend window: 2017-01 to 2018-08 (first/last empty months excluded, manual 11.5)

## Orders per month
| month | orders |
|---|---:|
| 2017-01 | 800 |
| 2017-02 | 1780 |
| 2017-03 | 2682 |
| 2017-04 | 2404 |
| 2017-05 | 3700 |
| 2017-06 | 3245 |
| 2017-07 | 4026 |
| 2017-08 | 4331 |
| 2017-09 | 4285 |
| 2017-10 | 4631 |
| 2017-11 | 7544 |
| 2017-12 | 5673 |
| 2018-01 | 7269 |
| 2018-02 | 6728 |
| 2018-03 | 7211 |
| 2018-04 | 6939 |
| 2018-05 | 6873 |
| 2018-06 | 6167 |
| 2018-07 | 6292 |
| 2018-08 | 6512 |

## Freight vs distance/weight/price (log-log regression)
- n=111420; full model R^2=0.542; distance-only R^2=0.289
- beta_log_dist=0.190 (freight % per 1% distance), beta_log_weight=0.155, beta_log_price=0.104

## Delivery time
- Pearson r(distance, delivery_days) = 0.393 (p=0)
- Pearson r(price, delivery_days) = 0.062
- on-time share = 0.936; mean late days among late = 10.5
