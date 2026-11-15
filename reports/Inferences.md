# Inferences — Algorithms, Pipelines, Results & Feature Dependencies

This document is the analytical core of the Olist-on-GrasPh engagement. It states **which GDS
(graph data science) and ML algorithms were used**, **how they are chained into pipelines**,
**how every number is interpreted**, and — crucially — **how one feature depends on another and
one result depends on another**. All figures were computed from the source CSVs, which the
GrasPh field manual (TASK 11.5 / 11.6) verified are **0-diff** against the stored graph
(568,960 nodes / 774,266 relationships), so source-derived numbers *are* the graph numbers.

Reproduce: `python3 analysis/proofs.py` (numpy only) then each `analysis/tasks/task0X_*.py`.

---

## 0. Environment & provenance

| Item | Value |
|---|---|
| Nodes / relationships | 568,960 / 774,266 (9 labels, 9 relationship types) |
| Item-level rows analyzed | 112,650 order items |
| Orders with a delivery date pair | 96,476 |
| Time window (full) | 2016-09 → 2018-10 |
| Time window (modeled) | 2017-01 → 2018-08 (boundary months near-empty) |
| Runtime | proofs 14/14 PASS; profiling 41 checks / 0 failures |
| Verification | source == graph (0 diff) + live-platform aggregates matched where auth allowed |

---

## 1. Master pipeline (how the tasks chain together)

```
 [9 source CSVs]  (0-diff to graph, manual 11.5/11.6)
      │
      ▼
 P2 · task01_profile ──► integrity, null-rate & cardinality baseline (41 checks, 0 fail)
      │
      ├──► P2 · task02_powerlaw ──► heavy-tail exponents & concentration (how skewed is supply?)
      │
      ▼
 P3 · task03_projections ──► 9 homogeneous projections (the ONLY way to get triangles:
      │                          stored schema is triangle-free — proof #6)
      ├── seller_shared_products      3,095n / 1,061e  (sparse)
      ├── seller_shared_categories    3,095n / 724,613e (dense, 100% connected)
      ├── seller_co_order             3,095n / 1,151e
      ├── product_bought_together    32,951n / 4,058e
      ├── category_shared_sellers        74n / 1,435e
      ├── product_same_category (clique), product_same_seller (clique)
      ├── order_product_incidence  (102,425e), person_projection (95,420 people)
      │
      ▼
 P4 · task04_graph_algorithms ──► centrality + community detection (igraph)
      │
      ├──► P5 · task05_link_prediction ──► future co-selling + association rules (temporal split)
      │
      ├──► P6 · task06_ml ──► late-delivery classifier + review-score regression (sklearn)
      │
      ├──► P7 · task07_nlp ──► Portuguese sentiment vs stars
      │
      ▼
 P8 · task08_timeseries_spatial ──► freight economics + delivery-time vs distance (haversine)
      │
      ▼
 PROOFS (14) + P9 verify + P10 synthesis ──► SYNTHESIS.md, ADVANCED_INSIGHTS.md, this file
```

Each phase consumes the one above it; **no phase re-derives a predecessor's numbers**, so an
error cannot silently propagate. Every projection ships with a manifest (label, node/edge counts,
weight definition) so the exact graph an algorithm saw is always named (TASK 11.9 rule 1).

---

## 2. GDS algorithms used — what, why, pipeline, result

### 2.1 Degree / connection count
- **What:** number of edges touching a node (per projection).
- **Why:** the cheapest way to see where value/density concentrates before running anything costly.
- **Pipeline:** count edges per node on each projection.
- **Result / interpretation:** On `seller_shared_categories` mean degree = **468** (max 2,686);
  on `seller_shared_products` mean degree = **0.69** (max 27). The ~680× gap says sellers overlap
  heavily on *category* but almost never on *identical SKUs* → competition happens at the
  category layer (see §4.3).

### 2.2 PageRank
- **What:** importance = share of random-walk mass that settles on a node
  (Google matrix `G = αP + (1−α)11ᵀ/n`, α = 0.85; proof #2 guarantees a unique stationary vector).
- **Why:** ranks *structural* influence, not just raw edge count — it rewards being connected to
  other well-connected nodes.
- **Pipeline:** power iteration on the undirected projection to convergence (residual ~1e-17).
- **Result / interpretation:** PageRank–degree Spearman ρ > 0.98 on every projection, **yet the
  top-10 by PageRank is not identical to the top-10 by degree**. Reading these as one number is a
  mistake: a seller with many *distinct* shared products sits centrally even when a mega-seller
  with private SKUs leads on volume (TASK 11.9 rule 3: always print the plain count next to it).

### 2.3 Betweenness centrality
- **What:** how often a node sits on the shortest path between two other nodes.
- **Why:** flags brokers/gatekeepers — the sellers that join otherwise separate communities.
- **Pipeline:** Brandes' algorithm, unweighted and price-weighted; compare ranks.
- **Result / interpretation:** weighted-vs-unweighted ρ = 0.92 on `seller_shared_products`.
  The top-5 betweenness sellers (`b2ba3715…`, `612170e3…`, …) are the bridges holding the 12.6%
  giant component together — remove them and co-seller discovery fragments.

### 2.4 k-core decomposition
- **What:** the largest k for which a node survives peeling all nodes of degree < k.
- **Why:** identifies the mutual-trust core that survives aggressive filtering.
- **Pipeline:** peel by degree until empty, record each node's core number.
- **Result / interpretation:** max k-core = **7** (sparse seller/product graphs) but **491**
  (dense `seller_shared_categories`). A k-core of 491 means ~490 categories genuinely co-occur
  per seller — the category layer is a real co-selling substrate; the SKU layer is not.

### 2.5 Connected components / giant component
- **What:** groups reachable from each other; the largest is the giant component.
- **Why:** separates the connected world from the long tail before trusting any centrality.
- **Result / interpretation:**
  | projection | isolates | giant | giant share |
  |---|---|---|---|
  | seller_shared_products | 2,309 | 390 | 12.6% |
  | seller_shared_categories | 0 | 3,095 | **100%** |
  | product_bought_together | 28,066 | 398 | 1.2% |
  The dense category projection is fully connected (ASPL 1.87, diameter 3 — "small world"),
  while 71.8% of the shared-product graph is isolated sellers. Any global average over the sparse
  graph would be misleading; the two projections must be reported separately.

### 2.6 Louvain community detection (+ null model)
- **What:** greedy modularity maximisation; `Q = Σ_c [ L_c/m − (D_c/2m)² ]` ∈ [−1/2, 1] (proof #3).
- **Why:** finds seller cohorts that share a category portfolio.
- **Pipeline:** run over **10 random seeds**, report modularity range + NMI vs seed 0; validate with
  a **degree-preserving rewiring null** (20 reps) and a permutation test (proof #12 guarantees the
  test's size).
- **Result / interpretation:** `seller_shared_categories` → **6–7 communities, Q = 0.356 ± 0.002**
  over 10 seeds. Null (rewired, same degrees) Q = **0.029 ± 0.0007**, permutation **p ≤ 0.05**.
  Because the null keeps every degree but destroys community structure, the 12× modularity gap
  cannot be explained by a few busy sellers — it is genuine category-driven clustering.

---

## 3. ML models used — what, why, pipeline, result

### 3.1 Late-delivery classifier (HistGradientBoosting vs Logistic Regression)
- **Target:** `late = delivered_customer_date > estimated_delivery_date` (prevalence **6.4%**).
- **Features (known at purchase time):** price, freight, weight/volume, installments, geographies,
  category, purchase day-of-week/month, seller state.
- **Split:** chronological (no leakage) — train 78,855 / test 33,795.
- **Why HGB:** handles non-linearity + missing values, robust to outliers; logistic is the
  convex baseline (proof #13) that guarantees a fair linear ceiling.
- **Result / interpretation:**
  | model | AUC | AP | vs baseline |
  |---|---|---|---|
  | HistGradientBoosting | **0.7758** | **0.2466** | +0.276 over 0.5; +0.182 over 0.065 prevalence |
  | Logistic regression | 0.6593 | — | +0.159 |
  → lateness is *largely* knowable before fulfilment (AUC≈0.78). AUC = P(random late ranked above
  random on-time) (proof #4 = Mann-Whitney concordance), AP = precision under ranking.

### 3.2 Review-score regression (with & without graph features)
- **Target:** `review_score` 1–5 (mean 4.035). Metric MAE / R².
- **Comparison:** tabular-only vs +graph features (seller degree, revenue, k-core).
- **Result / interpretation:** MAE **0.972** (tabular) vs **0.971** (tabular+graph); R²≈**0.08** both.
  Graph features add ~0.3% error reduction — inside noise. This is a **ceiling effect**, not a
  failure: 4.03/5 mean leaves almost no variance to explain (TASK 11.9 rule 3: state the count).
  Honest negative result.

### 3.3 Link prediction (CN / Jaccard / Adamic-Adar / Preferential Attachment)
- **Task:** rank future edges; temporal split (train < 2018-06-01, test ≥ 2018-06-01).
- **Why 4 heuristics:** CN is the count, Jaccard normalises, AA down-weights high-degree hubs
  (bounded by CN/log 2, proof #7), PA is the popularity null.
- **Result / interpretation:**
  | projection | best model | AUC | AP | prevalence |
  |---|---|---|---|---|
  | seller–seller (shared products) | **AA** | **0.746** | 0.0075 | 5.2e-05 |
  | product–product (bought together) | CN/Jacc/AA | ~0.50 | ~0 | 5e-06 |
  Seller co-selling is genuinely predictable (AA ≈ 0.75). Product co-purchase is **not** (≈ coin
  flip) — only 3.3% of orders carry ≥2 distinct products. PA on products scores *below* random
  (0.165): popular products already co-occur, so popularity is a misleading null here.

### 3.4 Association-rule mining (Apriori family)
- **Input:** 3,236 multi-product baskets. Support downward-closure is proven (proof #5) so pruning
  is lossless.
- **Result / interpretation:** top rules reach **lift up to 539** but support ≈ **0.19%**
  (≤ 41 of 3,236 baskets). High lift + tiny support = a real but *niche* pattern — good for curated
  bundles, useless for broad "you may also like".

### 3.5 Sentiment lexicon (NLP) vs review score
- **Method:** compact Portuguese polarity lexicon over 40,641 review messages.
- **Result / interpretation:** Spearman ρ(sentiment, score) = **0.55** (p ≈ 0; identical to Pearson
  on mid-ranks, proof #11). **235 inconsistencies** flagged (e.g. 5-star with negative text).
  Text and stars mostly agree → text is a usable proxy, with a small manual-QA tail.

---

## 4. Feature-dependency map (how one feature depends on another)

Pearson r (pairwise, item-level unless noted). Every arrow is a real dependency that constrains
which models are valid.

### 4.1 Delivery delay ← which bottleneck?
| stage | r(delay) | meaning |
|---|---|---|
| carrier transit (carrier→customer) | **0.569** | strongest driver |
| seller handling (approve→carrier) | 0.193 | secondary |
| payment approval (purchase→approve) | 0.042 | negligible |
→ **Delay is a last-mile / carrier-transit problem, not a seller-processing problem.** Interventions
targeting warehouses will barely move SLA; carrier routing & hub placement will. Survivorship
note: items without a `carrier_date` are excluded, so this is a *delivered-and-shipped* view.

### 4.2 Freight ← what?
| driver | r(freight) | log-log elasticity β |
|---|---|---|
| weight (g) | **0.610** | 0.155 |
| volume (cm³) | 0.583 | — |
| price | 0.413 | 0.104 |
| haversine distance (km) | **0.389** | **0.190** |
| weight × distance | −0.006 | no collinearity |
→ Distance is the **strongest single predictor** of the *share* of freight (β 0.19), while weight
explains the most raw correlation. Full log-log model **R² = 0.542 (54.2% of freight variance explained)** (n = 111,420); distance-only
R² = 0.289 (28.9% of freight variance explained). So **54% of freight is explainable pre-checkout** from distance+weight+price.

### 4.3 Distance ← the chain of costs (the master dependency)
```
 customer↔seller distance ─┬─► freight cost         (β 0.19, freight 12.6→44 R$ by band)
                          ├─► carrier transit days  (r 0.42)  ─► total delivery days (r 0.39)
                          └─► lateness (late rate 6.2%→13% by band) ─► review score (r −0.25)
```
Concrete banding (haversine):
| distance band | mean freight | late rate | mean review |
|---|---|---|---|
| < 200 km | R$12.65 | 6.2% | 4.17 |
| 200–500 km | R$19.12 | 6.9% | 4.02 |
| 500–1,000 km | R$21.13 | 8.1% | 3.99 |
| 1,000–3,000 km | R$31.50 | 11.4% | 3.91 |
| > 3,000 km | R$43.95 | 13.0% | 3.80 |
→ Distance is the **root cause** that cascades into cost, delay and satisfaction. Same-state vs
cross-state items look the same account for the whole gap: 154 km vs 849 km mean; freight R$13.5 vs
R$23.7; late 5.8% vs 8.8%. The supply side is concentrated in **São Paulo (71.3% of items)** but demand is
nationwide (São Paulo only 42.1% of customers) — the São Paulo↔rest of Brazil mismatch *is* the long haul.

### 4.4 Review score ← what actually moves it
| feature | r(review) |
|---|---|
| total delivery days | **−0.305** |
| delay days | **−0.247** |
| distance km | −0.055 |
| freight ratio | −0.040 |
| price | +0.003 |
→ The customer is disappointed by **waiting**, not by price or freight. On-time orders average
**4.15 stars**; late orders average **2.26** — a **1.9-star** swing, the single strongest effect in
the dataset. This is why graph features barely help review prediction (§3.2): the rating is set by
the delivery clock, which the seller graph only proxies.

**The delay → satisfaction dose-response (extra finding, measured per bucket):**

| delay bucket | n | mean review | % low (1–2★) |
|---|---:|---:|---:|
| on time | 102,076 | 4.21★ | 11.4% |
| 1–3 days late | 2,076 | 3.23★ | 34.0% |
| 4–7 days late | 1,937 | 2.09★ | 68.0% |
| 8–14 days late | 1,574 | 1.68★ | **80.1%** |
| 15+ days late | 1,469 | 1.71★ | 78.8% |

The damage is **monotone and front-loaded**: the share of 1–2★ reviews climbs 11% → 80% across the
first two weeks and then flattens (1.68★ vs 1.71★ past 8–14 days). Operational leverage therefore
sits in **preventing the first 3–7 days of slip**, which is exactly the window the late-delivery
classifier (§3.1) exposes ~10 days ahead.

### 4.5 Payment behaviour ← order value
- installments correlate with price (r = 0.307): bigger baskets are split more often.
- mix: credit_card **73.9%**, boleto 19.0%, voucher 5.6%, debit 1.5%.
- avg price by type: credit R$143.9 > boleto R$121.9 > debit R$120.7 > voucher R$116.9.
→ Credit card is the high-value default; boleto/debit skew to lower-value orders (no installments).

### 4.6 Category ← satisfaction & freight
- best rated (≥500 items): books_general_interest 4.45, luggage_accessories 4.32, food 4.22.
- worst rated: **office_furniture 3.49** (also highest freight R$40.5), furniture_decor 3.90,
  bed_bath_table 3.90.
→ Bulky furniture categories carry both the **highest freight** and the **lowest scores** — weight
  (§4.2) and fragile/large-item logistics stack into a double penalty.

**Add a third lever: supply concentration (HHI / Herfindahl–Hirschman Index).** office_furniture is
not only bulky — it is the **most seller-concentrated** live category (HHI ≈ 0.42, only 34 sellers),
while the best-performing health_beauty is the **most competitive** (HHI ≈ 0.02, 492 sellers).
Monopoly niches such as `cds_dvds_musicals` and `security_and_services` reach HHI ≈ 1.0 (one seller
owns the category). So a category's *structure* predicts its customer experience better than its
products do: **heavy + concentrated = freight, low rating and no price/service pressure at once.**

### 4.7 Supply concentration ← why projections differ
- top 1% of sellers = **26.42%** of items (power-law α = 2.381, p = 0.59, beats lognormal &
  exponential by Vuong). Bottom 50% of sellers hold **4.6%** of items.
- Full concentration curve (Lorenz): top 1% ≈ **26%**, top 5% ≈ **53%**, top 10% ≈ **68%** of items;
  **Gini = 0.79 (79.2/100, near-max inequality)** for both revenue and items (near-maximal inequality).
- only **1,225 of 32,951 products** are sold by >1 seller (96.3% single-source) → the
  seller-shared-product graph is sparse *by construction*, while the category graph is dense. This
  structural fact (not a modelling choice) is why the two projections give opposite connectivity
  pictures. **Money is concentrated in the head sellers, yet the catalogue is fragmented** — value is
  real but head-to-head price competition barely exists.

### 4.8 Churn signal ← weak by design
- repeat customers = 2,997 / 96,096 = **3.12%**.
- first-order score repeat 4.13 vs one-time 4.08 → ~0.05 rating difference, i.e. **the initial star
  rating is a weak churn predictor**. Retention is driven by factors not in the transaction table
  (merchandising, seasonality), so honest churn models must rely on engineered features, not raw
  review score.

### 4.9 Seller risk & the São Paulo-hub paradox (extra finding)
- **131 of 886 reviewed sellers (14.8%)** run late rates of **27–49%** against a hub benchmark most
  sellers sit far under (São Paulo average 8.33%). Risk is *concentrated in a tractable minority* — these
  are precisely the sellers the late-delivery classifier (§3.1) should flag before hand-off.
- **The São Paulo-hub paradox:** São Paulo has the **highest** seller-side late rate (**8.33%**) among the big hubs,
  while regional sellers are cleanest (Rio Grande do Sul 4.4%). The same concentration that makes São Paulo the supply
  capital is what spreads its **long-haul** lateness nationwide — São Paulo sellers ship the most far
  orders, and carrier transit (not their handling) is the delay driver (§4.1). The structural cause
  and the operational symptom are the same root: geographic over-concentration of supply.

---

## 5. One result on another (interpretation chain)

1. **No triangles (proof #6) → projections are mandatory.** Triangle count and local clustering on
   the raw schema are identically zero for every node. Any triangle-based metric must run on an
   explicit same-label projection; we report those (k-core, modularity) instead of pretending the
   raw graph has them.
2. **Sparse shared-SKU graph → degree and PageRank look different at the top.** Because most SKUs
   are single-seller, structural centrality (PageRank/betweenness) surfaces bridges the volume
   ranking hides — a seller-level recommendation signal that plain "top revenue" misses.
3. **Dense category graph → real communities.** Q = 0.356 vs rewired null 0.029 (p ≤ 0.05) means
   category-overlap clusters are statistically real, so seller cohorting by category is defensible.
4. **Distance → freight → delay → review is one causal chain.** Because each link is individually
   significant and monotone across distance bands, a regional-fulfilment intervention attacks cost,
   SLA *and* satisfaction at once — the highest-leverage single move.
5. **Ceiling at 4.03/5 → graph features add nothing to review.** Because most reviews are 5-star,
   there is little variance for any feature (graph or tabular) to explain; the honest report is
   "R² ≈ 0.08", not an inflated model claim.
6. **Weak cross-sell signal → spend effort on sellers, not products.** AA predicts future seller
   co-selling (AUC 0.746 (74.6% concordance)) but product co-purchase is a coin flip; budget link-prediction work
   accordingly.

---

## 6. Trust rules (TASK 11.9) — where each is satisfied

| rule | where satisfied |
|---|---|
| Name the projection (labels/types, n nodes/edges) | every P3 manifest + each section above |
| Random methods over several seeds, report range | Louvain 10 seeds (Q 0.356 ± 0.002), NMI range; permutation tests |
| Plain count next to every score | PageRank vs degree top-10; AUC vs prevalence/AP null |
| Ask whether chance gives the same | degree-preserving rewiring (20 reps, p ≤ 0.05); AUC-0.5 baseline |
| Say how many | 235/40,641 reviews; 67/153,287 test edges; 3,236/99,441 baskets |
| Cross-check the pull against GrasPh | task09 + manual 0-diff verification |

---

## 7. Limitations (guard the interpretations)

- Items without `carrier_date`/`delivered_date` are dropped from delay/freight regressions
  (96,476 of 99,441 orders) — a delivered-order view, not the full funnel.
- Distance uses zip-prefix centroids (haversine on sphere) — accurate to a few km, not street-level.
- Power-law fits are on discrete counts via the continuous approximation (Clauset et al. 2009);
  a large p *fails to reject*, it does not prove, a power law.
- Person order counts are right-censored at 2018-08.
- NLP uses a compact lexicon, not BERTimbau; 235 inconsistencies are the upgrade target.
- All results are **read-only** inference; no writes were made to GrasPh.
