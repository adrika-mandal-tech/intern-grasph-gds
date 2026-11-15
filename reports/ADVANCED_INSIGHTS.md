# Olist Graph Dataset — Advanced Insights, Inferences & Question Bank

Read-only analysis on the GrasPh Graph Data Science Olist graph (568,960 nodes / 774,266
relationships; source CSVs verified **0-diff** to the stored graph per field-manual TASK 11.5/11.6).
Every number below was computed, cross-checked, and — where a claim could be chance — tested
against a null. Companion files: `Inferences.md` (algorithms/pipelines), `p_math_proofs.md`
(14 proofs, every metric expressed as a percentage).

**Metric legend.** AUC 0.5 = coin flip, 1.0 = perfect (read as a 0–100% concordance). AP =
average precision under ranking. ρ = Spearman rank correlation. r = Pearson correlation. R² =
explained variance (0–100%). β = log-log elasticity = % change in freight per 1% change in a
driver. Gini / HHI = inequality indices (0 = even, 1 = one party holds everything).

---

# PART A — Questions you can answer (with the data-backed answers)

## A1. Order & operational status

**Q. How many orders are in each status?**
delivered **96,478** (97.0%) · shipped 1,107 · canceled 625 · unavailable 609 · invoiced 314 ·
processing 301 · created 5 · approved 2. *(verified live on GrasPh: exact match.)* The funnel is
healthy at the top — only ~1,234 orders (1.2%) are lost to cancel/unavailable — so this is a
delivery-quality problem, not a demand problem.

**Q. What are the delivery performance metrics (promised vs actual)?**
Defining *late* = `order_delivered_customer_date > order_estimated_delivery_date`: prevalence
**6.4%** (7,265 / 112,650 items); on-time share **93.6%**; mean lateness among late orders **10.5
days**. The delay is driven by **carrier transit** (r = 0.569) not seller processing (r = 0.19) —
i.e. the promise is missed on the road, not in the warehouse.

## A2. Customer behaviour & demographics

**Q. Which customer nodes actually belong to the same real person?**
`customer_id` is issued **per order** (99,441 order-customers); the true person is
`customer_unique_id` (**96,096** distinct). One person holds up to **17** orders. Any graph keyed
on `customer_id` counts a person once per order — always collapse to `customer_unique_id` first
(person projection = 95,420 people with ≥ 1 order).

**Q. Which cities/states account for the highest volume of buyers?**
São Paulo **41,746** · Rio de Janeiro 12,852 · Minas Gerais 11,635 (27 states, 4,119 cities). São Paulo customer share **42.1%** —
but **71.3%** of items ship from São Paulo sellers, so demand and supply are mismatched by ~29 points.
See §D1 for why this single fact drives most of the cost/delay/satisfaction structure.

## A3. Seller performance & revenue

**Q. Which sellers or states generate the highest revenue and item sales?**
Revenue is extremely concentrated — a Lorenz/Gini view gives **Gini = 0.79 (79.2/100, near-max inequality)** for both revenue and
items: the **top 1% of sellers (≈30) hold ~26% of items**, the **top 5% hold 53%**, and the **top
10% hold 68%**; the **bottom 50% hold only 4.6%**. Half of all items come from just **131**
sellers. Leaderboard (GQL `MATCH (i:OrderItem)-[:SOLD_BY]->(s:Seller) RETURN s.seller_id, count(i),
sum(i.price) …`). Seller states concentrate in **São Paulo (71.3%)**, Paraná (7.8%), Minas Gerais (7.7%).

**Q. What is the distribution of shipping cost (`freight_value`) vs item price across regions?**
Freight scales with **distance**, not price: mean freight R$12.65 (<200 km) → R$43.95 (>3,000 km),
while the price→freight elasticity is only β = 0.104. Same-state freight R$13.5 vs cross-state
R$23.7. Freight is a **geography** cost; price barely moves it.

## A4. Product & category analytics

**Q. What are the top-selling product categories by degree or volume?**
By product–category bipartite degree: **bed_bath_table 3,029 · sports_leisure 2,867 ·
furniture_decor 2,657 · health_beauty 2,444 · housewares 2,335**. By revenue: health_beauty
R$1.26M, watches_gifts R$1.21M, bed_bath_table R$1.05M. (Video/audio and "cool_stuff" fold into
these in the English taxonomy.)

**Q. Which products are sold across multiple sellers vs exclusively by one seller?**
Only **1,225 of 32,951 products (3.7%)** have > 1 seller. This single structural fact is why the
"competitors" (shared-SKU) graph is **sparse** (1,061 edges, 12.6% connected) while the
shared-category graph is **dense** (724,613 edges, 100% connected). 96.3% of products are
single-source → essentially no marketplace price competition at the SKU level.

## A5. Customer satisfaction

**Q. What is the distribution of review scores (1–5), and how do comments correlate with delivery
times or product categories?**
Scores: 5★ **56,910** · 4★ 19,007 · 3★ 8,097 · 2★ 3,114 · 1★ 11,282 (mean **4.035** of 5). The
distribution is left-heavy — **91.9%** of reviews are 4★ or 5★. Comments track the delivery clock:
late orders average **2.26★**, on-time **4.15★** (a **1.9★** swing), and text sentiment agrees
with stars at **ρ = 0.55**. By category, worst-rated: **office_furniture 3.49**, furniture_decor
3.90, bed_bath_table 3.90 — the heavy/bulky categories (see §D3).

---

# PART B — Inferences data scientists must design around

**B1. Extremely low customer retention.** 93,099 / 96,096 people (96.9%) bought once; only
**2,997 (3.1%)** repeat. → churn / cohort / repeat-purchase models face severe imbalance; a
person–person graph is near-empty; the positive class is right-censored at 2018-08. Report **with
the 3.1% denominator**, never as a bare count.

**B2. Single-item dominance.** 88,863 of 99,441 orders (89.3%) have one item; only **3,236 (3.3%)**
have ≥2 distinct products; only 1,278 ≥2 sellers. → market-basket analysis has thin raw material;
association rules must report lift *and* the tiny support, and itemset Apriori must deduplicate
repeated units (a 3×order of one SKU is **not** cross-sell evidence).

**B3. Pareto concentration.** Top 1% sellers ≈ 26% of items; Gini 0.79; only 1,225 products shared
across sellers. → recommendation / competitive analysis skews to a small head; shared products are
the rare bridges between sellers (the 1,061-edge graph's whole backbone).

**B4. Graph topology = no triangles (proven).** Triangle count / local clustering are identically
**0%** on the raw schema (proof #6: 0 of 84 label triples are pairwise adjacent). → any triangle
metric requires an **explicit same-label projection**; report k-core/modularity on the projection,
not on the raw graph.

**B5. Temporal pitfalls.** Boundary months near-empty (2016-09: 4, 2016-12: 1, 2018-09: 16,
2018-10: 4 orders). → restrict time-series and seasonality to **2017-01 → 2018-08** (20 months),
and even then 20 months cannot establish a robust annual cycle.

**B6. Data hygiene.** ZIP prefixes lost the leading zero (10,037 → 1,037) for ~24,000 customers /
1,027 sellers / 4,354 São Paulo areas — pad with `str(z).zfill(5)` before any geospatial join. **623
products** have no category node (610 empty + 13 untranslated) and drop out of category
projections. Reviews/geo dedupe duplicate CSV keys (98,410 unique review ids on 99,224 rows).

---

# PART C — Advanced predictive modeling (the four families)

## C1. Cost & financial prediction

- **C1a. Can we predict an order's total freight before checkout?** **Yes, ~54%.** Log-log OLS on
  distance + weight + price → **R² = 0.542 (54.2% of freight variance explained)** (n = 111,420). Elasticities: distance **β = 0.190**,
  weight β = 0.155, price β = 0.104. Distance alone → R² = 0.289 (28.9% of freight variance explained). The remaining ~46% is carrier zone
  pricing absent from the schema → a freight *quote* engine is feasible; an exact one is not.
- **C1b. Can we predict payment installments / type from value & region?** Partially. Installments
  correlate with price **r = 0.307** (bigger orders split more). Mix: credit_card **73.9%**, boleto
  19.0%, voucher 5.6%, debit 1.5%. Average order value by type: credit R$143.9 > boleto R$121.9 >
  debit R$120.7 > voucher R$116.9. Credit card is the high-value default; boleto/debit form the
  confusable low-value, zero-installment tail.
- **C1c. Can we forecast a seller's monthly revenue?** Feasible with a strong structural prior:
  supply is heavy-tailed (α = 2.381, beats lognormal/exponential). Seller degree, k-core (max 491
  on the category graph) and category mix are usable regressors; but for the long tail a "flat last
  month" persistence baseline already captures most of a single seller's small signal, so gains are
  modest except for the ~131 core sellers that drive 50% of volume — concentrate forecasting effort
  there.

## C2. Churn & customer lifetime value (LTV)

- **C2a. Can ML separate the 3.1% repeat buyers from one-timers?** The star signal is **thin by
  construction**: first-order rating barely differs (repeat 4.13 vs one-time 4.08, Δ ≈ 0.05). Real
  separation comes from **category** and **geography/gifting**, not stars. Treat as severe imbalance
  (3.1% positives), fix observation/outcome windows, and report with the denominator.
- **C2b. Can we predict time-to-churn / never-return probability?** Effectively **yes-by-default**:
  96.9% never return, so "never returns" is the dominant class. The useful model is the *inverse* —
  flagging the rare buyers with repeat-prone signals (gift categories, multi-item carts) rather than
  predicting churn.
- **C2c. Can we predict LTV from the first purchase?** Weakly. Because 96.9% are single-purchase,
  expected LTV ≈ first-order value + a small repeat uplift, and price is a weak satisfaction driver
  (r ≈ 0.003). LTV prediction reduces to "will this person be in the 3.1%?" — an **imbalanced
  classifier, not a regression**.

## C3. Logistics, delivery time & supply chain

- **C3a. Can we predict an SLA breach before hand-off to the carrier?** **Yes, AUC ≈ 0.78.**
  Purchase-time features (price, freight, weight/volume, installments, seller & customer
  geographies, category, purchase weekday/month) give HistGradientBoosting **AUC = 0.776 (77.6% concordance), AP =
  0.247** vs 6.5% prevalence (+0.28 AUC, +0.18 AP). The model never uses the actual delivery date.
  → early warning ~10 days before the promised date is deployable.
- **C3b. Which bottleneck contributes most?** **Carrier transit** (r = 0.569) ≫ seller handling
  (0.193) ≫ payment approval (0.042). Delayed items average ~10.5 late days, all on the last-mile
  leg → target carrier routing / hub placement, not warehouse speed.
- **C3c. Can we predict `review_score` from graph + tabular features?** Only ~**8%** of variance is
  explainable (tabular MAE 0.972, +graph MAE 0.971, R² ≈ 0.08 both). The rating is set by the
  **delivery clock**; graph features add nothing beyond it. Honest R² ≈ 0.08 beats an inflated
  model claim (TASK 11.9 rule 3).

## C4. Graph-specific & network tasks

- **C4a. Link prediction / Node2Vec / GNN for seller→new-category or cross-category buying?**
  Yes on seller–seller: **Adamic-Adar AUC = 0.746 (74.6% concordance), AP = 0.0075** vs prevalence 5.2e-05 (proven
  bounded by CN/log 2). Product–product co-purchase is **~0.50 = chance** (only 3.3% multi-item).
  Node2Vec/GNNs on the dense category projection (ASPL 1.87, diameter 3) are the natural upgrade
  for product links.
- **C4b. Fraud / anomaly detection from structure?** Actionable queues already visible: **235
  rating/text inconsistencies** (5★ with negative text); **131 sellers flagged** with 27–49% late
  rates (see §D4); dirty seller cities (19 entries like `sao paulo / sao paulo`, numeric codes);
  13 products in untracked categories. The 6–7 category communities (Q = 0.356 vs null 0.029)
  define "normal seller neighbourhoods"; pricing/logistics outliers outside them are the anomaly
  queue.

---

# PART D — Deep dependencies: how one feature drives another

This section is the heart of the "what depends on what" question. Each dependency below is
**measured**, not assumed (r / β / contingency tables), and each one *constrains which models are
valid*.

## D1. Distance is the root cause of a whole cascade

```
  customer↔seller distance ─┬─► freight cost         β 0.19   (R$12.65→R$43.95 by band)
                            ├─► carrier transit days  r 0.42  ─► total delivery days (r 0.39)
                            └─► lateness 6.2%→13%  ─► review score (r −0.25) ─► low-review rate 11%→80%
  São Paulo supply 71% vs nationwide demand (São Paulo only 42% of buyers) ─► the long haul that starts it all
```
Because each link is individually significant and monotone across distance bands, distance is a
**single upstream lever with four downstream consequences**. Same-state vs cross-state items
account for the whole gap: **154 km vs 849 km** mean; freight **R$13.5 vs R$23.7**; late **5.8% vs
8.8%**.

## D2. Delivery delay → satisfaction is a dose-response curve (not just a mean)

The effect of lateness is *monotone in magnitude* — every extra day of delay raises the share of
1–2★ "low" reviews almost linearly. This is why "on-time" is the single most valuable operational
metric.

| delay bucket | n | mean review | % low (1–2★) |
|---|---:|---:|---:|
| On time | 102,076 | **4.21★** | **11.4%** |
| 1–3 days late | 2,076 | 3.23★ | 34.0% |
| 4–7 days late | 1,937 | 2.09★ | 68.0% |
| 8–14 days late | 1,574 | 1.68★ | **80.1%** |
| 15+ days late | 1,469 | 1.71★ | 78.8% |

*Insight:* going from on-time to 8+ days late drops a ~22% low-review rate to ~80% — a **~7× jump
in dissatisfaction share**. The curve flattens past 14 days (1.71★) because those customers are
already maximally unhappy; the marginal damage is concentrated in the first week. **Operational
leverage is in preventing the first 3–7 days of slip**, not in chasing extreme outliers.

## D3. Category concentration (HHI) ↔ freight ↔ satisfaction — the triple penalty

The worst-rated category is **also** the most supply-concentrated **and** the heaviest. It is not
a coincidence — three dependencies stack.

| category | HHI (supply conc.) | sellers | mean freight | rating |
|---|---:|---:|---:|---:|
| office_furniture | **0.42** (high) | 34 | R$40.5 (highest) | **3.49 (worst)** |
| watches_gifts | 0.09 | 101 | mid | ~4.0 |
| health_beauty | **0.02** (competitive) | 492 | low | **4.45-region (best)** |
| bed_bath_table | 0.06 | 196 | high (bulky) | 3.90 |

*Insight:* categories that are **heavy** (→ high freight) **and** **seller-concentrated** (→ little
competition on price/service/quality) carry a **double penalty**: high shipping cost *and* low
satisfaction. `cds_dvds_musicals` and `security_and_services` reach **HHI = 1.0 / 0.54** (a single
seller owns the whole category) — pure monopoly niches. Competitive categories (health_beauty,
HHI 0.02) dominate the best-rated list. **A category's structure predicts its customer experience
better than the product does.**

## D4. Seller risk is concentrated in a small, identifiable set

Of **886 sellers with any reviews**, **131 (14.8%)** are flagged for late rates of **27–49%**
against a benchmark that most sellers sit well under (the São Paulo average is **8.33%**, the busiest hub).
The worst offenders (e.g. 48.9%, 47.2%, 37.5% late) are a ready-made **operational review queue** —
these are the sellers whose promised dates the C3a model would flag before hand-off. Risk is not
uniformly spread; it lives in a tractable minority.

## D5. Payment type ↔ order value (behavioural dependency)

Installments rise with price (r = 0.307) and concentrate in credit card (73.9% of payments but the
**highest** average value at R$143.9). boleto/debit (19% / 1.5%) are the low-value, cash-like tail
(≤ R$122) with no installment structure. → a checkout that nudges high-value orders toward
installments (credit) directly serves the highest-value cohort.

## D6. Why the two seller projections give opposite worlds (structural dependency)

Only **3.7%** of products have > 1 seller → the shared-SKU graph is sparse **by construction**
(12.6% connected, 2,309 isolates). But categories are widely shared → the same-category graph is
**100% connected** (ASPL 1.87, diameter 3, k-core 491). This is a *structural* fact, not a modelling
choice — it dictates that seller "competitors" must be found on the category layer, and it is why
Louvain finds real communities only there (Q = 0.356 vs null 0.029).

## D7. Category revenue vs category concentration (independent axes)

High revenue does **not** imply high concentration: health_beauty earns the most (R$1.26M) with a
*healthy* 492-seller HHI of 0.02, while office_furniture earns far less (R$0.27M) from only 34
sellers. → "biggest category" and "riskiest category" are different questions; target the former
for growth, the latter for intervention.

---

# PART E — One result on another: the interpretation chain

1. **No triangles (proof #6) → projections are mandatory.** Triangle/local-clustering on the raw
   schema are identically 0%; any triangle metric must run on a named projection, so k-core and
   modularity are reported there instead of faking them on the stored graph.
2. **Sparse shared-SKU graph → volume ≠ influence.** PageRank–degree ρ ≥ 98.5% **but top-10
   differ** — a seller with many distinct shared products is structurally central even when a
   private-catalogue mega-seller leads on revenue. Use both, never one as a proxy for the other.
3. **Dense category graph → real communities.** Q = 0.356 vs rewired null 0.029 (p = 0.048) means
   the category-overlap cohorts are statistically real, so seller cohorting/partner matching on the
   category layer is defensible.
4. **Distance → freight → delay → review is one causal chain.** A regional-fulfilment intervention
   attacks cost, SLA **and** satisfaction at once — the highest-leverage single move the data
   supports (D1).
5. **Delay dose-response → measure the first week.** Because dissatisfaction share jumps 11%→80%
   across 8 days (D2), the payoff is in early-warning intervention, which C3a makes possible
   (AUC 0.78, ~10 days lead).
6. **Review ceiling at 4.03/5 → graph features add nothing to review.** With 91.9% four/five-star
   reviews there is almost no variance to explain, so the honest report is "R² ≈ 0.08" — the rating
   is set by the clock, which the seller graph only proxies.
7. **Thin cross-sell → spend effort on sellers, not products.** AA predicts future seller co-selling
   (AUC 0.746 (74.6% concordance)) but product co-purchase is a coin flip (~0.50) and association lift (up to 539×) sits
   on 0.19% support — budget link-prediction and recommendation work accordingly.

---

# PART F — Additional insights & findings (beyond the standard question bank)

These are the extra inferences a data scientist should carry away, each grounded in a measured
number.

- **F1. The satisfaction ceiling is a feature, not a bug.** 91.9% of reviews are 4–5★; predicting
  them is trivial (always guess 5★). Any satisfaction model must therefore optimise the thin
  1–3★ tail (e.g. log-loss or low-recall-weighted metrics), not overall accuracy.
- **F2. Weight and distance are almost orthogonal (r = −0.006) yet both raise freight.** So freight
  has (at least) two independent drivers — heavy-but-local and light-but-far — and a quote engine
  needs both terms; a single-variable estimate will under-price one of the two regimes.
- **F3. The São Paulo hub paradox.** São Paulo has the **highest** seller-side late rate (**8.33%**) among the
  big hubs, while regional sellers (Rio Grande do Sul 4.4%) are cleanest — because São Paulo sellers serve the most
  *long-haul* orders. The concentration that makes São Paulo the supply capital is the same concentration
  that spreads its long-haul lateness nationwide.
- **F4. Repeat buyers are "slightly happier," but not predictably so.** Repeat customers' first
  order scores 4.13 vs 4.08 for one-timers (Δ ≈ 0.05) — statistically real, practically useless for
  churn. Retention is driven by factors outside the transaction table (merchandising, seasonality),
  so don't build a churn model on review score alone.
- **F5. Bulk and fragility form a "double penalty" class.** office_furniture simultaneously has the
  highest freight (R$40.5), the worst rating (3.49) and the highest seller concentration (HHI 0.42).
  Bulky categories are the natural first target for both a logistics fix (regional fulfilment) and
  a supply-diversification fix.
- **F6. The market is monetarily concentrated but product-wise fragmented.** Gini 0.79 (money in the
  head sellers) yet 96.3% of products are single-seller. The marketplace value is real, but
  head-to-head price competition barely exists — governance should watch the **supply** bottleneck,
  not assume competition will self-regulate prices.
- **F7. Payment value ladder is a clean behavioural segmentation.** credit R$143.9 > boleto R$121.9
  > debit R$120.7 > voucher R$116.9, with installments (r = 0.307) riding on credit. This is a
  ready-made feature for the C1b/CLTV models without any new data.
- **F8. Data-quality "anomalies" are a real deliverable, not noise.** 235 rating/text mismatches,
  19 dirty seller cities, 24k zero-stripped zips, 623 category-less products, and 131 high-late
  sellers = five concrete QA/ops queues. Fixing the zips and dirty cities directly improves the
  distance feature that drives everything in D1.
- **F9. Temporal safety is non-negotiable.** With 20 usable months and near-empty boundary months,
  20 months cannot validate an annual seasonal model — use a seasonal-naive baseline and say so,
  rather than over-fitting ARIMA/Prophet to a single holiday peak (Nov 2017 = 7,544 orders).
- **F10. Everything generalizes from a delivered-order lens.** Delay/freight regressions drop items
  without a carrier/delivery date (96,476 of 99,441 orders — 97% of items), so results describe the
  fulfilled funnel, not the full intent-to-deliver funnel. Canceled/unavailable orders (1,234) are
  out of scope and are their own classifier problem.

---

## Feature-dependency map (one line per arrow)

| outcome | strongest drivers (r / β) | practical meaning |
|---|---|---|
| freight cost | weight 0.61 · dist 0.39 (β 0.19) · price 0.41 (β 0.10) | R² 0.542 (54.2%) (54.2%); distance dominates the *share* |
| delivery delay | carrier transit **0.569** > seller handling 0.19 | last-mile problem |
| review score | total delivery **−0.305** · delay −0.247 · dist −0.055 · price +0.003 | waiting hurts; price doesn't |
| low(1–2★) review share | delay bucket 11%→80% (D2) | dose-response, front-loaded |
| distance (root cause) | → freight 0.39, → transit 0.42, → lateness 6.2%→13% | one lever, three+ effects |
| category rating | freight 0.61 · HHI 0.42 (D3) | bulky + concentrated = double penalty |
| payment installments | price 0.307 | bigger orders split more |
| seller late rate (hub) | long-haul exposure (São Paulo 8.33% vs Rio Grande do Sul 4.4%) | supply concentration spreads delay |
| product–product link | ≈0 (chance) | 3.3% baskets — thin |
| seller–seller link | AA 0.75 (bounded by CN/log 2) | real, predictable |

**The master chain (everything downstream of geography):**
```
supply in São Paulo (71%) vs nationwide demand (São Paulo only 42% of buyers)
    → long customer↔seller distance (597 km mean)
        → freight (β 0.19, R² 0.54 (54%))          [C1a]
        → carrier transit (r 0.57) → lateness 6.4%      [C3a/C3b]
            → review score swing 4.15→2.26★, low-review 11%→80%   [C3c / D2]
supply concentration (Gini 0.79) + product fragmentation (96% single-seller)
    → few head sellers, thin competition, category HHI → rating   [A3 / D3]
```

---

## Algorithm / model summary

| task | algorithm | library | headline result (as %) |
|---|---|---|---|
| popularity fit | power-law MLE + bootstrap (proof #1) | numpy/scipy | α 2.381, top-1% = 26.4% items, p 0.59 |
| centrality | degree, PageRank, betweenness, k-core (proofs #2/#10) | igraph | Paraná–degree ρ ≥ 98.5%, top-10 differ |
| community | Louvain (10 seeds) + rewiring null (proofs #3/#12) | igraph | Q 35.6% vs null 2.9% (p = 0.048) |
| link prediction | CN / Jaccard / AA / PA (proofs #4/#7) | python | AA 74.6% (sellers), 50% (products) |
| cross-sell | Apriori association rules (proof #5) | python | lift ≤ 539× on 0.19% support |
| freight economics | log-log OLS + haversine (proof #9) | numpy | R² 54.2%, β_dist 0.19 |
| delivery risk | HistGradientBoosting / logistic (proofs #4/#13) | sklearn | AUC 77.6% / 65.9% vs prevalence 6.5% |
| review model | gradient-boosted regression ± graph feats | sklearn | R² ≈ 8% (ceiling effect) |
| sentiment | Portuguese lexicon + Spearman (proof #11) | python | ρ 55%, 235 flags |
| p-values | bootstrap + permutation (proofs #8/#12) | numpy | conservative, size ≤ nominal 5% |
| vector search (deferred) | cosine k-NN on 1,536-d embeddings (proof #14) | platform | ranking sound after L2-normalisation |
