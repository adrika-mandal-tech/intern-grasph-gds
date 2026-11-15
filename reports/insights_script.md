# `insights.html` — Delivery Script (Story Deck)

**How to use this script:** Say it out loud while the matching section is on screen. Each part follows: what I did → what came out → why it matters → what/when/how/why. It covers every tile, card, dashboard, table, and section from the hero to the closing Q&A. Read it naturally — these are your words.

---

## Hero section (home / top of page)

I want to open with the big picture. On screen is the hero of the story deck. The title reads: "Distance moves everything — Olist on GrasPh." The lede explains that on a flat table, the data is 112,650 order items, each standing alone. On the graph, every item links to its seller, customer, product, and zip codes — and a single cause — how far the customer sits from the seller — cascades into freight, carrier delay, and the star rating. Every figure was computed from the source CSVs, verified zero-different from the stored graph.

Below that are five headline tiles:
- **Tile one:** 54% — of freight predictable before checkout (R² 0.542)
- **Tile two:** 78% — AUC ranking a late order above an on-time one — at purchase time
- **Tile three:** 1.9★ — drop when an order runs late (4.15 → 2.26)
- **Tile four:** 36% — modularity of real seller communities (null 2.9%)
- **Tile five:** 0.79 — Gini of seller revenue — head sellers earn it all

I'll come back to each of these numbers in the sections that follow. For now, the audience should leave knowing the headline story: distance is the root cause driving freight cost, delivery delay, and customer satisfaction; revenue is dangerously concentrated; seller communities are real but modest; and the top sellers earn most of the money.

**What:** hero framing and five headline tiles.
**When:** opening the story deck, before any section.
**How:** tiles with big numbers and plain-language labels.
**Why:** to give the scorecard up front before walking through the derivation of each number.

**Say it like this:** "Five numbers frame the story: freight 54% predictable, lateness ranked at 78% AUC at purchase time, a 1.9-star drop when orders run late, seller communities at Q 0.357 vs a 0.029 null, and revenue Gini 0.79. Every one of these traces back to distance."

---

## Open (introductory paragraph)

Before I walk through the sections, let me set the context. I am walking you through a data-science investigation on a Brazilian e-commerce marketplace called Olist. I worked with 99,441 orders and 112,650 order items from September 2016 to October 2018 across 27 Brazilian states, run on a graph platform called GrasPh.

**Three screens:** this one is the story — what happened in the business. The second screen is the method — how I built the graph. The third is the machinery — formulas, classifiers, diagnostic matrices, and the Brazil map. If you ask where a number came from, it is on one of the other two screens.

**Why graph, not a spreadsheet:** as a table it is 112,650 independent rows and every question degrades to an average. So I profiled the structure first, and three findings shape everything. The schema is bipartite — projections were mandatory. Four boundary months are near-empty — any trend through them is an artefact. And customer↔seller distance isn't in the database — I derived it for all 112,650 items with the haversine formula. That derived edge is the root cause of every finding here.

**Say it like this:** "This screen is the story — what happened in the business. Three things shaped everything: the schema is bipartite so projections were mandatory, four boundary months are near-empty so trends through them are artefacts, and customer-to-seller distance isn't in the database — I derived it with the haversine formula. That derived edge is the root cause of every finding here."

---

## Section 1 — Distance is the root cause

This section establishes that distance is the single upstream driver of cost, delay, and dissatisfaction.

**What I did:** I split order items into distance bands based on customer↔seller haversine distance derived from ZIP-prefix centroids (Proof #9), then averaged freight cost, late rate, and rating within each band.

**What came out — distance bands dashboard:**

| Distance Band | Mean Freight | Late Rate | Mean Rating |
|---|---|---|---|
| < 200 km | R$12.65 | 6.2% | 4.17★ |
| > 3,000 km | R$43.95 | 13.0% | 3.80★ |

I also computed the mechanism: 71.3% of sellers sit in São Paulo, but only 42.1% of buyers do. Mean distance per item is 597 km (median 432 km). The platform manufactures long hauls — sellers are concentrated in one state while demand is nationwide.

**Why it matters:** Not that any single number is large, but that all three metrics degrade monotonically along the same axis. If freight rose but lateness didn't, that's a cost problem only. If lateness rose but ratings didn't, customers forgive waits. Neither is the pattern — one latent variable (distance) drives three metrics, so this is one recommendation, not three.

**Answers:**
- **What:** freight cost, late rate, and rating by distance band.
- **When:** first section of the story, establishing root cause.
- **How:** haversine distance per item, banded averages, seller/buyer state distribution.
- **Why:** to prove distance is the single upstream driver of cost, delay, and dissatisfaction.

**Say it like this:** "Freight, lateness, and rating all get worse as distance grows — not one number in isolation, but three metrics degrading along the same axis. One latent variable, distance, drives all three. Mean distance is 597 km because 71% of sellers are in São Paulo but only 42% of buyers are — the platform manufactures long hauls."

---

## Section 2 — The cascade

This section traces how distance forks into cost and time, both reconverging on lateness and then ratings.

**What I did:** I fit a log-log OLS model for freight economics and computed Pearson correlations for carrier transit vs delivery days, then linked lateness to review scores.

**What came out:**

**Cost:** ln(freight) = ln A + β₁ln(dist) + β₂ln(wt) + β₃ln(price). Log-log because freight is multiplicative — a 1% longer journey adds a fixed percentage, not a fixed number of reais — so each β is an elasticity (% freight change per 1% predictor change). Results: β_distance 0.190, β_weight 0.155, β_price 0.104; full R² 0.542, distance alone 0.289 — all three terms needed.

**Time:** r(carrier transit, delivery days) = 0.569 vs seller handling 0.19, approval 0.04. Transit dominates — so the fix is the carrier network, which is a function of distance.

**Both routes reconverge on lateness:** r = −0.258 across 111,461 items, ~6.7% of rating variance — the largest controllable effect in the dataset.

**Why it matters:** Every link is individually significant, monotone, and has a mechanism. Distance → freight cost + carrier transit → late delivery → lower rating is one chain.

**Answers:**
- **What:** the causal cascade from distance to freight, carrier time, lateness, and rating.
- **When:** after distance bands, before structure.
- **How:** log-log elasticity regression; Pearson correlations for transit/handling/approval vs delivery days; delay vs rating correlation.
- **Why:** to show exactly how distance becomes cost and delay, and where the leverage points are.

**Say it like this:** "Distance forks into cost and time. Cost: log-log elasticities — distance 0.190, weight 0.155, price 0.104; R² 0.542. Time: carrier transit r 0.569 dominates seller handling 0.19. Both reconverge on lateness, and lateness drives the rating down at r −0.258 — one chain, every link significant."

---

## Section 3 — Structure: two projections, opposite worlds

This section shows that seller communities exist but live on the shared-category projection, not the shared-product projection.

**What I did:** I built two seller projections — shared-product and shared-category — and compared their topology, modularity, and centrality.

**What came out:**

**Product×product:** Only 3.7% of products (1,225 of 32,951) are sold by more than one seller. Of 99,441 orders, just 3,236 (3.3%) hold ≥2 products. That graph is shattered — no recommender possible.

**Seller×category:** One dense small world. Leiden over 10 seeds gives Q = 0.357. Modularity Q = (1/2m)Σ_c[e_c − a_c²] is the excess of within-community edges over degree-preserving random rewiring. The null: rewiring gives 0.029 — so ~12× stronger than chance, stable across 10 seeds. Communities are real, not a seed artefact.

**But:** PageRank and degree correlate at ρ = 0.988 — near-perfect in aggregate — yet the top-10 lists differ on every projection. Conclusion: a bridge seller can be structurally central without being a volume leader, so ranking by revenue and targeting misses the sellers holding the network together.

**Why it matters:** The structural fact (96.3% of products single-seller) decides where communities exist. Volume ≠ structure. The dense category layer (modularity 36% vs 2.9% chance) is where seller cohorts, partner-matching, and competitive analysis actually live.

**Answers:**
- **What:** two seller projections — shared-SKU (sparse) vs shared-category (dense) — with modularity and centrality comparison.
- **When:** after cascade, before concentration/delay cliff.
- **How:** Jaccard-style co-occurrence weights; Leiden modularity with 10 seeds; rewiring null; Spearman ρ PageRank vs degree.
- **Why:** to prove seller communities are real but distinct from categories, and that structural influence ≠ commercial volume.

**Say it like this:** "Two projections, opposite worlds. Shared-product graph is shattered — only 3.7% of products have a second seller. Shared-category graph is one dense small world at Q 0.357 vs a 0.029 null — twelve times stronger than chance. PageRank and degree agree overall (ρ 0.988) but their top-10 lists differ — structural influence and volume are not the same ranking."

---

## Section 4 — Concentration and the delay cliff

This section combines revenue concentration (Gini) with the delay cliff (rating vs delay buckets).

**What I did:** I computed the Gini coefficient over 3,095 sellers ranked by revenue, and split reviewed items by lateness bucket to show the dose-response.

**What came out — Concentration:** Gini 0.792 — bottom 50% of the 3,095 sellers earn ~3% of revenue, top 1% earn 25.7%, top 5% earn 49.1%, half of all items flow through 131 sellers. ~9 sellers hold a quarter of the business: losing ~9 sellers erases 25% of revenue.

**Delay cliff:** On-time 4.21★ / 11.4% low → 1–3 days 3.23★ / 34.0% → 4–7 days 2.09★ / 68.0% → 8–14 days 1.68★ / 80.1%. Monotone — a gradient, not one cliff. Front-loaded — the first 3 days cost ~1★ and take low reviews from 11.4% to 34.0%, while 15+ days changes essentially nothing. Recovery window is the first 7 days.

**Honest caveat:** This is a correlation (r = −0.258), not an experiment. I act on it because the lateness classifier hits AUC 0.7758 from purchase-time features alone, putting delay upstream of the rating.

**Why it matters:** Concentration and delay are the two biggest structural facts in the dataset — a few sellers hold most revenue, and delay is the largest controllable driver of dissatisfaction.

**Answers:**
- **What:** Gini concentration + delay-bucket rating/cliff.
- **When:** after structure, before predictability.
- **How:** Gini formula over seller revenue; delay buckets by calendar day; Pearson r for delay vs rating.
- **Why:** to show both the revenue risk (seller head) and the satisfaction risk (delay cliff) in one section.

**Say it like this:** "Gini 0.792 — bottom half of sellers earns ~3%, top 1% earns 25.7%. And the delay cliff: 4.21 stars on time, 1.68 stars two weeks late; low-review share climbs from 11% to 80%. It's a correlation, but the lateness classifier at AUC 0.776 puts delay upstream of the rating."

---

## Section 5 — What's predictable, and what isn't

This section ranks every prediction task and gives an honest verdict on each.

**What I did:** I evaluated freight prediction, late-delivery classification, review-score regression, cross-sell link prediction, and churn modeling — each with appropriate metrics and baselines.

**What came out:**

**Freight:** R² 0.542 — a pre-checkout quote is feasible at 54.2%; an exact per-item forecast is not, because the residual 45.8% is carrier zone pricing absent from the schema.

**Lateness:** HistGradientBoosting — gradient-boosted trees, each tree fitting the forest's residuals — on purchase-time features only, never the delivery date. Prevalence 6.4% (1 in 16), which is why I report AUC 0.7758 and AP 0.2466 rather than accuracy. ~10 days of warning before the promised date.

**Review score:** Graph features move MAE 0.974 → 0.971, R² = 0.081 against a mean of 4.03/5. Why that's the right answer: a ceiling effect — 91.9% of reviews are 4–5★, so there's barely any variance left to explain. Model the 1–3★ tail, not the population.

**Cross-sell:** All four heuristics — common neighbours, Jaccard, Adamic-Adar, preferential attachment — score AUC 0.50, i.e. chance. Apriori finds lift up to 539× but on 0.19% support — that's ~19 orders. Curate bundles; don't build a broad recommender.

**Why it matters:** I report ceilings, not inflated claims. Lateness is predictable at purchase time; freight is partially predictable; reviews are ceiling-bounded; cross-sell is thin.

**Answers:**
- **What:** predictability verdicts for freight, lateness, review score, cross-sell.
- **When:** after concentration/delay cliff, before the decision.
- **How:** log-log R² for freight; HistGradientBoosting AUC/AP for lateness; MAE/R² for review score; AUC for link heuristics; Apriori lift/support for cross-sell.
- **Why:** to set honest expectations about what the data can and cannot support.

**Say it like this:** "Freight is 54% predictable — good enough for a quote, not an exact forecast. Lateness ranks at 78% AUC at purchase time — ten days of warning. Reviews top out at R² 0.081 — a ceiling effect, model the tail not the population. Cross-sell is a coin flip at AUC 0.50 — curate bundles, don't build a recommender."

---

## Section 6 — The decision

This section synthesizes everything into a single recommendation plus operational queues.

**What I did:** I combined all findings — distance root cause, freight/delay/rating chain, concentration, communities — into one actionable recommendation and a set of anomaly queues.

**What came out:**

**The decision:** Regional fulfilment is the only lever here that moves cost, speed, and satisfaction simultaneously, and each of those three links is individually significant. São Paulo has the worst hub late rate at 8.33% while Rio Grande do Sul is cleanest at 4.4% — not a quality problem, just the most long-haul exposure. So don't leave São Paulo; add capacity outside it.

**Anomalies as deliverables:** 235 rating/text mismatches, 19 dirty seller cities, 24k zero-stripped zips, 623 category-less products, 131 high-late sellers → five ops queues.

**Not claimed:** No next step is done; each targets a measured ceiling — product links above 0.50, reviews above 0.081, freight above 0.542.

**Why it matters:** The story ends with one actionable decision (regional fulfilment) and five concrete queues, with honest ceilings stated so nothing is oversold.

**Answers:**
- **What:** the final recommendation and ops queues.
- **When:** closing the story deck, before Q&A.
- **How:** synthesis of all previous sections; anomaly counts from data quality checks.
- **Why:** to give the audience a clear decision and next steps, not just numbers.

**Say it like this:** "Regional fulfilment is the only lever that moves cost, speed, and satisfaction at once. São Paulo has the worst hub late rate at 8.33% while Rio Grande do Sul is cleanest at 4.4% — not a quality problem, just long-haul exposure. Don't leave São Paulo; add capacity outside it. And here are five ops queues: rating/text mismatches, dirty seller cities, zero-stripped zips, category-less products, high-late sellers."

---

## Q&A

This section answers the questions an audience is most likely to ask about the story deck.

**What I did:** I prepared direct numeric answers grouped by topic, each tracing back to numbers already shown on the three screens.

**What came out:**

- **Real data?** 568,960 nodes / 774,266 relationships, verified 0-different from the source CSVs, read-only.
- **Lateness accuracy?** AUC 0.7758 = 77.6% concordance vs 6.4% prevalence, at purchase time.
- **Why not accuracy?** A predict-on-time-always classifier scores 93.6% at that prevalence.
- **Communities real?** Q 0.357 vs 0.029 null (p = 0.048), stable across 10 seeds; category-only projection far weaker at Q 0.100.
- **Anything beat the delivery clock?** No — ~0.3 MAE points.
- **Which states matter?** São Paulo: 80,564 items = 53.4% of demand, R$8.6M revenue, 8.3% hub late rate. Hover any state on the third screen for all 5 metrics; click for rank out of 27.

**Why it matters:** Every answer traces to a number already shown on one of the three screens — nothing is asserted on faith.

**Answers:**
- **What:** answers to the most common audience questions.
- **When:** at the end of the presentation.
- **How:** direct numeric answers grouped by topic.
- **Why:** so you can answer confidently without hunting for sources.

**Say it like this:** "Every number here has a derivation, a null test, and a cross-check against the stored graph — nothing is asserted on faith."
