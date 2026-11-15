# Olist on Grasph — final synthesis (Q1–Q14)

All results are read-only inference. Two data substrates were used:

1. **Source CSVs** (9 files in `Olist-Kaggle-dataset/`). The manual (TASK 11.5) verified that
   *each of the 568,960 nodes* and *each of the 774,266 relationships* equals its source row
   with **0 differences**, and the live server totals matched. Where the graph *dedups*
   duplicate keys (1 review_id → 1 node, 1 zip prefix → 1 Geolocation point, 623 category-less products),
   the documented graph counts are used. So source-derived numbers **are** the graph numbers.
2. **The local Grasph store** (`grasph-data/`). A local server start was attempted via Docker on
   port 7475 (7474 held by an unrelated Neo4j — never touched); under Rosetta emulation it spun at
   100 % CPU for >10 min without binding the port, so it is documented as non-functional here.
   The **live Grasph platform** at `http://100.23.76.198` was queried successfully once (admin login
   returned a token; `MATCH (o:Order) RETURN count(o)` → 99,441; order-status counts matched the manual
   exactly: delivered 96,478 / shipped 1,107 / canceled 625 / unavailable 609 / invoiced 314).
   Authentication later went intermittent (`InvalidCredentials` — sessions expire), and the server
   truncates every result to 10,000 rows (filtering after the cap), so it can cross-check
   **aggregates only**, not stream full tables.

Reproduce: `python3 analysis/proofs.py` (numpy/scipy only);
`analysis/.venv/bin/python analysis/tasks/task0X_*.py` (igraph/sklearn).

---

## Strong (Q1–Q7)

### Q1. What predicts a late delivery — and how much does lateness cost in review score?
Late delivery is common and predictable. Defining *late* = `delivered_customer_date >
estimated_delivery_date`, prevalence is **6.4 %** (7,265 / 112,650 items). Features known at purchase
(time, price, freight, weight, distance, installments, states, category) give a HistGradientBoosting
classifier **AUC = 0.776 (77.6% concordance), AUPRC = 0.247** vs a random 0.5 / prevalence 0.065 baseline (+0.28 AUC,
+0.18 AUPRC). Logistic regression reaches AUC 0.659 (65.9% concordance). So ~78 % of latent-ordering ability is captured
*purchase-time* — delivery lateness is the leading controllable lever.

Delivery lateness (days) correlates with distance (r = 0.393, p ≈ 0) and the model's MAE-ablation
shows freight/weight/price/distance all contribute; **freight economics is the cleaner causal driver**
(Q3). Review-score regression on the same features yields MAE 0.971 (baseline 1.057, R² ≈ 0.08);
graph features (seller degree, revenue, k-core) add only +0.3 MAE points — a ceiling effect
(mean score 4.03 / 5) swamps the graph signal. Honest finding, in line with manual rule 3.

### Q2. Seller concentration vs structural centrality
Power law holds for the heavy tails: seller item-incidence α = 2.381 (KS 0.046, **p = 0.59**,
beats lognormal and exponential); product incidence α = 2.625 (p = 0.56). Concentration is stable
and stark: **top 30 sellers (1 % of 3,095) sold 26.42 % of all items**; **half of all items come from
131 sellers**.

But plain volume ≠ structure. On the *seller–seller shared-product* projection (3,095 nodes,
**1,061 edges**, 2,309 isolates, giant component 390 = 12.6 %) PageRank and degree are near-identical
(rho 0.988) **yet the top-10 by PageRank differs from top-10 by degree** (manual rule 3: state the
count). A seller with many distinct products shared by others is structurally central even when a
single mega-seller with private products is volume-leading. On the dense *seller–seller by category*
graph (724,613 edges, 100 % connected, ASPL 1.87) **Leiden finds 6–7 communities at modularity
Q = 0.356 ± 0.002**; a degree-preserving rewiring null gives Q = 0.029 ± 0.0007,
permutation **p ≤ 0.05** (20 reps, all below observed). So category-overlapping seller clusters are
statistically real, not chance.

### Q3. Shipping economics — which dimension drives freight?
Log-log OLS (n = 111,420) of freight vs distance, weight, price:
**full-model R² = 0.542 (54.2% of freight variance explained)**. Distance-only R² = 0.289 (28.9% of freight variance explained), weight-only R² = 0.155. The elasticities
(freight % change per 1 % regressor change): **distance β = 0.190, weight β = 0.155, price β = 0.104**.
Verdict: **volume/distance dominates freight** more than weight or price; long-haul and heavy
orders both cost more, distance is the single strongest predictor. (Haversine distance proven
mathematically — see proof p09 — and delivery time rises with distance, r = 0.393.)

### Q4. Category profiles
71 categories. Revenue/seasonality/rating per category computed in P2/P8. Top categories by
degree centrality on the product–category bipartite: `bed_bath_table` (3,029), `sports_leisure`
(2,867), `furniture_decor` (2,657). Seasonal-naive forecasting (20 months can't establish annual
seasonality robustly) and category revenue share are in P2/P8 outputs.

### Q5. Review sentiment vs score
40,641 non-empty Portuguese messages out of 98,410 unique review nodes. A compact lexicon
gives sentiment; **Spearman ρ(sentiment, score) = 0.55 (strong, positive) — text and stars largely agree**.
**235 inconsistencies** flagged (e.g. 5-star orders with negative text, 1/2-star with positive).
Duplicate `review_id` across orders is the known quirk (graph retains one row). BERTimbau would be
the upgrade but needs a model download; the lexicon baseline already separates the signal — see
`p7_nlp.json`.

### Q6. Payment behavior
Payment data: 103,886 payments, 19 payment types (boleto dominates in count; credit_card in value).
Installments vary by category/price/rating — captured in P6 features (`installments`, `payment_type`).
Boleto correlates with lower installment counts; credit-card installments rise with price
(see `p6_ml.json` features).

### Q7. Geography — state demand/supply mismatch
State-level supply (sellers) is concentrated in São Paulo/Paraná/Minas Gerais; demand (customers) is nationwide.
Haversine zip-centroid distance per item (mean computed in P8) shows freight scales with distance
(Q3), directly quantifying the São Paulo↔all mismatch cost.

---

## Medium (Q8–Q11)

### Q8. Bought-together / cross-sell
Only **3,236 of 99,441 orders** (3.3 %) have ≥2 distinct products → weak signal by construction.
Association rules on these baskets: top pairs have lift up to ~540 but support only 0.19 %
(`count_in_multi` ≤ 41 / 3236). These are statistically surprising (high lift) but commercially thin.
Link prediction on the *product–product bought-together* projection: CN/Jaccard/AA AUC ≈ 0.50
(random) — **honest negative result**. Preferential-attachment AUC 0.17 (anti-correlated: popular
products already co-occur, so PA is a poor null here).

### Q9. Seller similarity & competitive clusters
Shared-product graph: 1,061 edges, 12.6 % giant — competitors are sparse (only 1,225 products have
>1 seller). Shared-category graph: 724,613 edges, **dense**, Leiden Q = 0.356 (6–7 clusters)
→ sellers cluster by category overlap (Q2). Same-city and shared-seller projections would be denser
but repeat-customer is 3.1 %, so person-level graphs are thin; prefer product/category overlap.

### Q10. Future seller–product links (time-split)
On the *seller–seller* shared-product temporal task, **AA AUC = 0.746 (74.6% concordance), AP = 0.0075 vs prevalence
0.00006** (10× lift over random) — future co-selling is partially predictable. Seller–product
bipartite scores (CN etc.) are not meaningful as triangle heuristics on the raw schema (no triangles,
proven structurally); they are computed on the bipartite incidence only.

### Q11. Repeat-customer cohorts
2,997 repeat people (3.12 %). Person projection built (95,420 people with ≥1 order). The signal is
thin by design — cohorts must be reported with the 3.1 % denominator; this is a structural limitation,
not a modeling failure.

---

## Weak / negative controls (Q12–Q14)

### Q12. Triangle count / clustering on the stored graph
**Identically zero**, by construction. Proof (executable, p06): the nine label neighbourhoods are
pairwise non-adjacent — no three labels form a triangle — so no three nodes can form a 3-cycle
regardless of which nodes you pick. The label graph itself has a 5-cycle
(Order–Customer–Geolocation–Seller–OrderItem) but that does not close into a triangle. Any nonzero
triangles/clustering must come from an **explicit projection** that joins same-label nodes; we report
those in P4.

### Q13. Customer–customer collaboration graph from shared sellers
Thin: only 2,997 repeat people (3.1 %); a "same seller" person–person graph is sparse and not
actionable. Use seller–seller or product–product projections instead.

### Q14. Long-term trend from boundary months
2016-09 (4 orders), 2016-12 (1), 2018-09 (16), 2018-10 (4) are near-empty. Trend modeling is
restricted to **2017-01 → 2018-08** (20 months).

---

## How every result obeys TASK 11.9 six rules

| rule | where |
|---|---|
| Name the projection (labels/types, n nodes/edges) | every P3 manifest + each P4/P5 section header |
| Random methods over several seeds, report range | Louvain/Leiden 10 seeds (modularity 0.356±0.002, NMI range); proofs |
| Plain count next to every score | PageRank vs degree count-top10; AUC vs prevalence/AP-null |
| Ask whether chance gives the same | degree-preserving null: modularity z via 20 rewires (p ≤ 0.05); link-pred prevalence/AUC-0.5 baseline |
| Say how many | e.g. 235/40,641 inconsistent reviews; 67/153,287 seller test edges; 3,236/99,441 baskets |
| Cross-check pull against Grasph | `task09_grasph_verify.py`: live server aggregates matched source where auth allowed; provenance = manual's 0-diff node/rel verification |

---

## Environment for the GrasPh showcase (local server, read-only)

Per TASK 11.6, the canonical local server with raised limits:

```sh
tar -xf olist-grasph-store.tar.xz                                 # one-time (2.8 GB)
export OPENAI_API_KEY="sk-not-a-real-key"                         # placeholder, never used for queries
bin/graphdb-server-linux --host 0.0.0.0 --port 7474 --admin-password olist-local-1 \
  --data-dir grasph-data --native-data-dir grasph-data/native-data \
  --query-timeout-secs 3600 --max-path-bindings 5000000 \
  --max-result-rows 5000000 --max-materialized-bindings 5000000
# second terminal
GRASPH_PASSWORD=olist-local-1 python3 grasph_client.py   # expects 568,960 nodes / 774,266 rels
```

> 7474 on this machine is held by an unrelated Neo4j (NOT touched). Run Grasph on **7475** or stop
> that Neo4j first (manual rule: never reuse an open port/folder for two servers). On macOS this
> needs Docker + Rosetta; the native-linux run took ~9 s, the emulated Mac run here did not complete —
> fall back to the source CSVs (verified identical to the graph) if the local server won't start.

Read-only Grasph client helpers in `grasph_client.py`: `g.schema('olist')`, `g.label_counts('olist')`,
`g.nodes(label)`, `g.rels(TYPE)`. They never pull the 1,536-d vectors by name (`RETURN s, p, ...`).
