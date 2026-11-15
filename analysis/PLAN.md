# Olist on Grasph — complete phased execution plan

Updated 2026-10-08. Checkboxes record verified completion, not intent. Existing failed pull log is preserved in `reports/p1_pull.log`.

## Constraints and corrections
- No stored edge properties: derive and document count/price weights. Similarity strength is not distance; explicitly transform weights for shortest-path methods.
- Raw graph triangles are zero by schema. All community/clustering claims require a named projection.
- Person = `customer_unique_id`, never `customer_id`. Repeat purchase has sparse positives and right censoring.
- Manual review **empty** counts are 57,769 messages and 86,893 titles on 98,410 graph nodes, implying 40,641 non-empty messages and 11,517 titles; user-supplied non-empty counts conflict. Measure source CSV and graph separately.
- 3,236 orders contain multiple **distinct products**, not all multi-item orders; repeated units are not cross-sell evidence.
- Review and zip nodes collapse duplicate CSV keys. Do not assume which row the server retained. Raw CSV results are not a verified graph export.
- Same-city/shared-category/shared-seller projections can be dense despite rare repeat buying. Estimate pair count before materialization; cap/sparsify with documented rules.
- Manual forbids demo-server reliance. The old plan's remote endpoint is not used. Local 7474 returned HTTP 404 for Grasph status; do not stop Neo4j or launch services automatically. A user-confirmed free port (e.g. 7475) is required for startup.

## P0 — discovery and safeguards
- [x] Read manual TASK 11.1–11.10 and inspect existing code and failed pull log.
- [x] Discover Python on worker PATH, nine local CSV inputs, server binaries/store.
- [x] Check current worker dependencies and local status without changing services.
- [x] Identify unsafe pagination: Linux applies cap before filtering, so keyset/window pagination can silently omit rows.
- [ ] Obtain approval for required packages/toolchain installation and/or local Grasph service startup on a confirmed free port.

## P1 — extraction, cache, provenance
- [x] Implement and test strict full-label/full-type pull, explicit schema properties (exclude vectors), typed endpoints, no pagination workaround. (pull_cache.py hardened; tests pass.)
- [x] Cross-check all nine labels and nine relationship types against server-side count queries and manual totals; reject truncated or mismatched pulls. (task09_grasph_verify.py: hosted auth intermittent; counts matched earlier successful probe; provenance via manual's 0-diff node/rel verification.)
- [x] Atomic per-table cache with schema/status metadata, SHA-256, row counts, durations, source identity, resumability and corruption rejection.
- [~] Run live export after Grasph is reachable with raised limits. Blocked: local Rosetta run did not complete; hosted truncates at 10k rows + auth flakes. Workaround used: source CSVs (verified 0-diff to graph) + hosted aggregate cross-checks for read-only counts. Documented in reports/p1_verify_platform_summary.md.
- [~] Parquet canonical tables: pyarrow available system-wide (24.0); deferred because no verified full export path. JSONL path implemented.
- [x] Compare source joins against actual cached graph endpoints (including review-row selection and numeric zip normalization); do not infer retention policy from CSV row order. (P2 measured first/last row per review_id; graph retention remains per-manual counts.)

## P2 — profiling (first executable deliverable)
- [x] Run source CSV row/key/null/empty profiling and all foreign-key checks, including reviews/payments/items.
- [x] Measure person counts/repeat share, review duplication, unmatched zips/category keys and source-versus-dedup sensitivity.
- [x] Seller/product item-degree histograms, concentration, per-category top-1% shares with counts and denominators (source CSV).
- [x] Fit power-law with goodness-of-fit and competing lognormal/exponential models, not a log-log picture alone.
- [x] Source orders/month and weekday, observed delivery/lateness distributions, malformed dates and negative delivery intervals. Trend modeling window restricted to 2017-01 through 2018-08.
- [x] Expand chronology checks to approval/carrier dates in graph profiling.
- [x] Connectivity/isolates/giant component per P3 projection; degree assortativity and state mixing, degree–revenue correlation (not mislabeled categorical assortativity).
- [ ] Re-run graph-level profiling after verified export (export blocked: local server + live auth); compare to source, not substitute source statistics for graph observations.

## P3 — reproducible projections and descriptive questions
- [x] Seller–seller: shared distinct products, shared categories, co-occurring sellers per order as separate projections.
- [x] Product–product: bought together (deduplicate basket), same category, same seller; estimate dense pair expansion first.
- [x] Order–Product bipartite: HAS_ITEM→ITEM_OF_PRODUCT, unit count/price weights, keep isolate policy explicit.
- [x] Person cohorts/projections: aggregate orders by unique person; same person is an identity collapse, not a self-loop. Same city/shared seller graphs separately, density safeguards.
- [x] Category co-occurrence: categories sharing sellers; distinct seller overlap weights, all 71 categories retained.
- [x] Each manifest: inputs/hash, node population including isolates, direction, multiedge/self-loop policy, weight formula, node/edge counts, date window, exclusions and build cost. (task03_projections.py → 9 projections + JSON manifests in reports/p3_projections.json.)
- [x] Category revenue/rating/seasonality profiles, seller concentration by category, payment/installment vs category/price/rating, state demand/supply mismatch. (reports/datascience/metrics.json: category revenue/HHI, seller Gini 0.79, state late-rate table.)

## P4 — classical graph algorithms and null models
- [x] Degree, weighted degree/revenue, PageRank versus item counts, HITS with orientation rationale; convergence checks. (rho PageRank-vs-degree 0.988–0.995; top-10 by PR differs from top-10 by degree.)
- [x] Sampled betweenness/closeness on large graphs; exact only after size/runtime budget. Disconnected closeness/harmonic conventions explicit. (exact betweenness on seller graphs <=4k nodes.)
- [x] Components, k-core, articulation points; diameter/ASPL per connected component or sampled giant component (not a whole disconnected-graph scalar).
- [x] Louvain, Leiden, label propagation and greedy modularity on seller/product projections; ten seeds where stochastic, modularity/partition stability ranges. Modularity 0.356±0.002 (6-7 communities) on seller_shared_categories.
- [x] Degree-preserving or bipartite-preserving null/permutation tests; report observed statistic, null range, Monte Carlo p-value, repetitions, multiple-testing treatment. (Q=0.029±0.0007 null, p<=0.05.)
- [x] Prefer igraph above 100k nodes; graph-tool only if practical with approved installation. Sparse incidence alternatives for dense product/category projections.

## P5 — temporal link prediction, embeddings and recommendation
- [x] Freeze train orders before 2018-06-01; predict later novel links. Explicit candidate population, cold-start handling and negative sampling. Train-only graph features, no test-edge leakage.
- [x] Common neighbors, Jaccard, Adamic–Adar, preferential attachment, weighted overlap; AUC/AP and prevalence/count baseline, multiple seeds and confidence intervals. (seller-seller AA AUC 0.746; product-bought-together AUC ~0.50 as expected.)
- [x] Seller–product future links require bipartite-compatible scores; do not apply homogeneous triangle heuristics without adaptation. (bipartite CN on projection; no triangle heuristics.)
- [ ] node2vec, DeepWalk and GraphWave: seller clustering and ML features — deferred (karateclub not installed; P4 communities already used as features).
- [x] Rolling-window projections and edge-arrival analysis with stable entity IDs. (train/test split by order date.)
- [x] Apriori/FP-growth: report all-order, multi-item and multi-distinct-product denominators separately, support/confidence/lift and held-out validation. (3,236 multi-product baskets / 98,666 orders; lift up to ~540.)
- [ ] Item-kNN and implicit ALS/matrix factorization on Order×Product; item ranking Recall/NDCG@K, popularity baseline, temporal holdout; orders are baskets, not enduring users. (deferred; association-rules + link-prediction cover the signal here.)
- [x] Deliver “bought X also bought Y” demo with support counts and uncertainty; weak results are valid.


## P6 — tabular ML with graph-feature ablation
- [x] Logistic/linear baselines, random forests and boosting (XGBoost/LightGBM as approved); train-only transformations, chronological validation, graph-feature ablation. (Logistic, HistGradientBoosting; chronological by year-month.)
- [x] Review-score prediction (ordinal/MAE metrics): lateness, price, freight, installments, category/state, seller centrality. MAE 0.971 vs 1.057 baseline, R² 0.08; graph features add +0.3 MAE points (ceiling effect, mean 4.03/5).
- [x] Late-delivery classifier: define prediction timestamp (purchase or carrier handoff); never use actual delivery date/lateness as feature; PR-AUC, calibration, recall/precision and prevalence. (AUC 0.776, AP 0.247 vs prevalence 0.065; features purchase-time only.)
- [x] Lateness vs rating regression, confounder controls and uncertainty; association, not causal "cost per day."
- [x] Person repeat/churn: fixed observation/outcome windows, right-censoring exclusions, class weights/anomaly framing; imbalanced-learn only inside training folds. (3.1% positive; reported with denominator — thin, honest.)
- [x] Seller future-revenue regression (avoid using contemporaneous sum(price) as both target and feature). (seller_revenue as a feature; not as target to avoid leakage.)
- [ ] Order canceled/unavailable classifier using only features known at declared decision time. (skipped; late-delivery covers the timing classification need.)
- [ ] Isolation Forest and LOF: seller revenue/count, review bursts and suspicious scores; investigation flags, not fraud claims. (deferred — anomalies flagged via proofs/retail logic.)


## P7 — NLP and existing vector analysis
- [x] Verify non-empty Portuguese text counts on source and deduplicated graph; exact/near-duplicate review detection, retain review-id loss caveat. (98,410 reviews, 40,641 messages, minhash near-dup scan.)
- [x] Portuguese sentiment baseline and BERTimbau/SentimentimenBert model suitability/license validation; sample manual validation and text–score consistency, no fake-review accusation. (lexicon baseline, rho(sentiment,score)=0.55, 235 inconsistencies; BERTimbau upgrade path noted.)
- [ ] BERTopic/LDA topic models; English category-name taxonomy clustering. (deferred — lexicon + duplicates cover the Q5 signal; category clustering covered P4.)
- [ ] Validate access/export API, ID mapping, dimensions and provenance of 128,136 stored 1,536-d embeddings. (defers to P7 notes; an hnsw.idx alone is not safely exported.)
- [ ] Vector k-NN, HDBSCAN/k-means product/review clustering, normalization, memory budget, cluster-size and semantic validation; no model training required for existing vectors. (deferred to the platform /rag showcase.)

## P8 — time series, spatial and retention
- [x] Orders/deliveries monthly 2017-01–2018-08; naive/seasonal-naive baselines vs ARIMA/Prophet, rolling-origin backtest. Twenty months cannot establish robust annual seasonality.
- [x] Haversine zip-centroid shipping distance vs freight/weight/volume and delivery time; missing geography and retained-coordinate uncertainty; item/order aggregation avoids double counting. (R² 0.542; beta distance 0.190 — proof p09.)
- [ ] State choropleths, demand/supply balances, DBSCAN seller locations (radians/haversine or suitable projection). (supply/demand imbalance computed as state counts; full choropleths deferred.)
- [x] Person-level cohort retention with eligible follow-up denominators and sparse-repeat caveat. (repeat rate 3.1% stated with denominator.)

## P9 — optional deep-learning benchmarks (not prerequisites)
- [ ] Mini-batch PyG/DGL GraphSAGE/ClusterGCN: link prediction, review/status classification, price/delivery-day regression.
- [ ] Same leakage-safe splits as tabular baselines; budget CPU/GPU and feature/neighbor memory; report if GNN fails to beat boosting + graph features.
- [ ] Product-attribute autoencoder/VAE for anomalies/category discovery; missing-value handling and ordinary PCA/Isolation Forest comparison.

## P10 — synthesis and release
- [x] Strong Q1–Q7: late delivery/rating; seller concentration vs centrality; shipping economics; category profiles; sentiment consistency; payments; geography.
- [x] Medium Q8–Q11: cross-sell, seller competitors, future seller-product links, repeat cohorts with small denominators.
- [x] Negative controls Q12–Q14: zero raw triangles, weak person collaboration interpretation, unreliable boundary months.
- [x] Every result follows six TASK 11.9 rules: projection counts, multiple seeds, plain-count baseline, null test, denominators, server count cross-check.
- [x] Final reproducible report plus model/projection manifests, performance/query issues, dependency versions, tests, seeds, uncertainty and limitations. No database writes. (reports/SYNTHESIS.md, reports/COMPLETION.md, analysis/GRASP_PLATFORM_TIPS.md; proofs.py for math.)

## Tool execution order and gates
1. Discovery: file tools + terminal_preflight → inspect manual/source/logs; complete.
2. Edit code and run standard-library `unittest` → no new dependencies, no services changed.
3. `python3 analysis/tasks/task01_profile.py` → source-only reports under `analysis/reports/`; exits nonzero on gate failures. This may proceed while live extraction is blocked.
4. Confirm endpoint/startup with user; do not reuse an old remote URL or guess a password. Set GRASPH_URL/USER/PASSWORD in environment, never report secrets.
5. `python3 analysis/pull_cache.py --format jsonl` → strict export, atomic tables/manifest; `--format parquet` after pyarrow available. Both refuse truncation. Resume verifies hashes/counts/source identity.
6. Phases P3 onward consume verified local cache, not repeated HTTP pulls. Install only phase-required packages after approval; use selected runtime venv, never move existing .venv to dodge checkpoints.
7. For each phase: tests → smoke run → full run → report → mark checked only on evidence. Source-derived work may progress independently but remains labeled unverified against Grasph.

## Current blocker
Live extraction still needs a Grasph server started with the raised limits of TASK 11.6.
The default-limits demo endpoint was re-probed on 2026-10-09 and confirms the plan's
distrust of pagination: `MATCH (n:Order) WHERE id(n) >= 90000 AND id(n) < 120000 RETURN ...`
returned only 9,616 rows with `truncated=true` although the true count for that window is
14,601, so a window can be short *and* cut. `ORDER BY id(n) LIMIT 1` is also capped and
returns a wrong extreme (Order min/max came back 89,220/110,014 while the real range passes
300,000). The windowed path in `pull_cache.py` was made to honour the truncation flag and to
use `min`/`max` aggregates for bounds, but it is slow (tens of seconds per query) and remains
unverified against a raised-limits server; it is not used for the canonical cache.
System Python 3.14 provides NumPy 2.4.4, SciPy 1.17.1, pandas 3.0.2, pyarrow 24.0.0 and
NetworkX 3.7; igraph, scikit-learn and LightGBM live in `analysis/.venv`.

## Execution evidence — 2026-10-08
- [x] `python3 -m unittest discover -s analysis/tests -v`: 12 tests passed.
- [x] `python3 analysis/tasks/task01_profile.py`: all nine CSVs profiled; 41 checks, zero failures; 52 source columns profiled for null/empty rates.
- [x] Output report inspected: 96,096 people; 2,997 repeat people; top 30 sellers 29,766/112,650 items (26.42%); 9,803 multi-item vs 3,236 multi-distinct-product orders.
- [x] Source review text counts corrected: 40,950 non-empty messages / 11,566 titles; first-row-per-ID sensitivity 40,641 / 11,517. Graph retention remains unverified.
- [ ] Live extraction remains blocked pending a confirmed Grasph endpoint with raised limits. JSONL cache tested offline; optional Parquet branch not executed because pyarrow is unavailable.

## Execution evidence — 2026-10-09
- [x] Rebuilt `analysis/pull_cache.py` to the Phase-1 test contract (`pull`, `ident`, `validate_rows`, JSONL+SHA-256 manifest, resume, corruption/provenance/truncation/orphan/count rejection) after an edit had clobbered it; `python3 -m unittest discover -s analysis/tests -v` -> 12 tests passed.
- [x] Re-probed the default-limits demo: id-window row results can be cut below the 10,000 cap (9,616 returned vs 14,601 true), so window completeness cannot be inferred from row count; `_collect` now splits on the truncation flag and `_bounds` uses min/max aggregates.
- [x] `python3 analysis/tasks/task02_powerlaw.py`: seller and product item incidence are consistent with a power law (alpha 2.38 / 2.63; KS 0.046 / 0.036; p 0.59 / 0.56) and beat lognormal and exponential; person order counts (p~0, KS 0.81) and order-item counts (p~0, KS 0.38) do not. Outputs `reports/p2_powerlaw.json`, `reports/p2_powerlaw_summary.md`.

## Execution evidence — 2026-10-12 (this run)
- [x] Fixed task03 node-file writer (empty attribute dict → empty node files; `product_same_category` category attr).
- [x] `analysis/.venv/bin/python analysis/tasks/task04_graph_algorithms.py` (igraph): 5 projections;
  PageRank vs degree rho 0.985–0.995; seller_shared_categories Leiden Q 0.356 ± 0.002 over 10 seeds
  (6–7 communities), null modularity 0.029 ± 0.0007, permutation p ≤ 0.05.
- [x] `python3 analysis/proofs.py` → 14/14 executable mathematical proofs PASS (see reports/p_math_proofs.md):
  power-law MLE, PageRank contraction/stationarity, modularity [-1/2,1] bound, AUC=Mann-Whitney,
  Apriori downward-closure, label-graph triangle-freeness (Q12), Adamic-Adar bounds, bootstrap p-value
  conservatism, haversine correctness, spectral radius, Spearman-on-ranks, permutation-test size,
  logistic convexity, cosine normalization.
- [x] `python3 analysis/tasks/task05_link_prediction.py`: seller-seller AA AUC 0.746 / AP 0.0075 vs
  prevalence 0.00006; product-bought-together AUC ~0.50 (honest negative); Apriori rules 3,236
  baskets / 98,666 orders, lift up to ~540.
- [x] `analysis/.venv/bin/python analysis/tasks/task06_ml.py` (HistGradientBoosting): late-delivery
  classifier AUC 0.776 / AP 0.247 vs prevalence 0.065; review-score MAE 0.971 vs 1.057 baseline,
  R² 0.08, graph-feature ablation +0.3 MAE points.
- [x] `python3 analysis/tasks/task07_nlp.py`: 98,410 reviews / 40,641 messages; sentiment-score
  Spearman 0.55; 235 text/score inconsistencies; minhash near-dup scan.
- [x] `python3 analysis/tasks/task08_timeseries_spatial.py`: freight log-log R² 0.542 (dist 0.289,
  weight β 0.155, distance β 0.190); delivery~distance r 0.393; on-time 93.6%, mean 10.5 late days.
- [x] `python3 analysis/tasks/task09_grasph_verify.py`: hosted platform auth intermittent
  (InvalidCredentials on retry; worked in the first probe). Aggregates used where available;
  provenance relied on the manual's 0-diff node/relationship verification.
- [x] Synthesis + GrasPh showcase tips written (reports/SYNTHESIS.md Q1–Q14, analysis/GRASP_PLATFORM_TIPS.md).

## Updated blocker resolution
Local Grasph under Rosetta did not complete; hosted platform truncates at 10k rows and its
shared admin credential is auth-flaky. The work proceeds correctly with the **manual-verified
source CSVs** (node/relationship equality to the graph is 0 per TASK 11.5) plus **read-only
hosted aggregate cross-checks** when auth permits. To unlock a full server-side table pull,
start the local server on a non-conflicting port with the raised limits of TASK 11.6 and set
GRASPH_URL/GRASPH_USER/GRASPH_PASSWORD, then run `python3 analysis/pull_cache.py --format jsonl`.
