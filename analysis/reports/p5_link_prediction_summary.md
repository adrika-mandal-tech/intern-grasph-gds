# Phase 5 — temporal link prediction & association rules

Time split: train < 2018-06-01, test >= 2018-06-01

## Seller–seller (shared products)
- candidates: 153287, test edges: 67, prevalence: 0.0001
  - CN: AUC=0.7458, AP=0.0054
  - Jaccard: AUC=0.7451, AP=0.0044
  - AA: AUC=0.7464, AP=0.0075
  - PA: AUC=0.5146, AP=0.0002

## Product–product (bought together)
  - CN: AUC=0.4998, AP=0.0000
  - Jaccard: AUC=0.4998, AP=0.0000
  - AA: AUC=0.4998, AP=0.0000
  - PA: AUC=0.1653, AP=0.0000

## Association rules (multi-product baskets)
- multi-distinct-product orders: 3236 / 98666 total orders
  - ['1dc7685f4fdb9622d84ae2ec658d5bbf'] -> ['e256d05115f9eb3766f3ab752132a4e2']: sup_cond=0.0012, conf=0.667, lift=539.33
  - ['e256d05115f9eb3766f3ab752132a4e2'] -> ['1dc7685f4fdb9622d84ae2ec658d5bbf']: sup_cond=0.0012, conf=1.000, lift=539.33
  - ['e6b314a2236c162ede1a879f1075430f'] -> ['ad4b5def91ac7c575dbdf65b5be311f4']: sup_cond=0.0019, conf=1.000, lift=539.33
  - ['ad4b5def91ac7c575dbdf65b5be311f4'] -> ['e6b314a2236c162ede1a879f1075430f']: sup_cond=0.0019, conf=1.000, lift=539.33
  - ['5d790355cbeded0cd60e25cbc4c527a2'] -> ['5fc3e6a4b52b0c414458104ed4037f1c']: sup_cond=0.0019, conf=1.000, lift=539.33
  - ['5fc3e6a4b52b0c414458104ed4037f1c'] -> ['5d790355cbeded0cd60e25cbc4c527a2']: sup_cond=0.0019, conf=1.000, lift=539.33
  - ['5b8a5a9417210b1b84b67b9a7aefb935'] -> ['e5ae72c62ebfa708624f5029d609b160']: sup_cond=0.0019, conf=1.000, lift=462.29
  - ['dbb67791e405873b259e4656bf971246'] -> ['18486698933fbb64af6c0a255f7dd64c']: sup_cond=0.0022, conf=1.000, lift=462.29
  - ['18486698933fbb64af6c0a255f7dd64c'] -> ['dbb67791e405873b259e4656bf971246']: sup_cond=0.0022, conf=1.000, lift=462.29
  - ['0d85c435fd60b277ffb9e9b0f88f927a'] -> ['ee57070aa3b24a06fdd0e02efd2d757d']: sup_cond=0.0019, conf=1.000, lift=462.29
