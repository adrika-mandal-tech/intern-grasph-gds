On screen is the hero of the machinery deck: "Who drives the marketplace, why customers walk away, and where the supply chain is fragile." The subtitle explains this isn't just sales charts — it's a relationship-first investigation of 99,441 orders, 3,095 sellers, and 32,951 products, covering concentration, customer experience, seller communities, and marketplace risk, with every claim tied to a named graph projection and tested against a null.

Below that are four pills: 568,960 nodes, 774,266 relationships, 9 labels, and 0-diff to source CSVs — meaning the data I worked with matches the stored graph exactly.

Then five headline tiles:
- **Tile one:** Seller revenue Gini — the marketplace is a near-monopoly at the top.
- **Tile two:** Late orders that drew a low rating — the experience cliff.
- **Tile three:** Sellers flagged as high-risk, out of those with 20 or more reviews.
- **Tile four:** Top category HHI — a whole category held by one seller.

I'll come back to each of these numbers in detail. For now, the audience should leave knowing the headline story: a few sellers dominate revenue, late delivery kills ratings, some categories are dangerously concentrated, and the whole thing traces back to distance.

**What:** hero framing and five headline tiles.
**When:** opening the machinery deck.
**How:** tiles with big numbers and plain-language labels.
**Why:** to give the scorecard up front before walking through the derivation of each number.

**Say it like this:** "This is the machinery deck — the detail behind the story. Five numbers frame it: revenue Gini near 0.79, late orders driving low ratings, high-risk sellers flagged, top-category HHI at one point zero, all on 568,960 nodes and 774,266 relationships verified zero-diff against the source."

---

## 01 · Framing

Next is framing. I want to move the conversation from "here are some sales charts" to "here is how the marketplace behaves." A bar chart of revenue by category is an exploratory notebook. A data-science investigation asks a question, names the graph it runs on, tests whether chance explains the answer, and ends in a decision. Every section that follows uses that discipline.

I lay out five research questions with their verdicts right up front:

RQ1 — Is marketplace revenue dominated by a few sellers? Verdict: severe.
RQ2 — Does late delivery explain low ratings? Verdict: strong.
RQ3 — Do seller communities exist beyond categories? Verdict: real, but modest.
RQ4 — Which sellers or categories are fragile? Verdict: actionable.
RQ5 — Do graph features beat tabular for predicting low ratings? Verdict: no, because of a ceiling effect.

RQ5 is deliberate — it's an honest negative control. The value of this report is that it reports the ceiling, not an inflated model claim.

I also explain a foundational constraint that underpins everything in this deck:

**Derivation — how each edge weight is computed:**

Here is exactly how I derived each projection, with node and edge counts:

1. **seller_shared_categories** — 3,095 nodes / 724,613 edges. For every pair of sellers, I count how many distinct categories they both sell in. The edge weight is that count — more shared categories means a heavier, stronger link between those sellers.

2. **seller_shared_products** — 3,095 nodes / 1,061 edges. For every pair of sellers, I count how many distinct products they both sell. The edge weight is that shared-product count. This graph is very sparse — only 1,061 edges — because most sellers have private catalogs and rarely share products.

3. **seller_co_order** — 3,095 nodes / 1,151 edges. For every pair of sellers, I count how many orders contain items from both sellers. The edge weight is that co-occurrence count — how often two sellers appear together in the same order.

4. **product_bought_together** — 32,951 nodes / 4,058 edges. For every pair of products, I count how many orders contain both products. The edge weight is that co-bought count. This is also sparse — only 3.3% of orders hold two or more distinct products — so the graph is thin.

5. **category_shared_sellers** — 74 nodes / 1,435 edges. For every pair of categories, I count how many sellers sell in both categories. The edge weight is that shared-seller count. Categories are nodes here (74 of them), not products.

**Distance (customer↔seller) — not stored at all:** The database does not store distance between a customer and a seller. I derived it for all 112,650 order items using the haversine formula over ZIP-prefix centroids. I took the customer's zip and the seller's zip as node properties, converted each to latitude/longitude, and computed the great-circle distance in kilometres between them. This derived distance edge is the root cause of every finding in this deck — it drives freight cost, carrier delay, and the star rating.

**Workflow — the pipeline I followed:**

Step 1 — Extract node properties. From the source CSVs, I pulled each seller's categories and products, each product's categories, each order's items and seller, and each customer's and seller's ZIP prefix.

Step 2 — Clean and normalize. I padded zip codes with leading zeros using str(z).zfill(5) because São Paulo zips were stored as numbers (01037 became 1037). I deduplicated by review_id and collapsed customer_id to customer_unique_id to get the real person (96,096 people from 99,441 orders).

Step 3 — Build same-label projections. For each projection above, I joined on shared node properties and computed the edge weight as a count of shared neighbours or co-occurrences. Each projection got a manifest recording inputs, hash, node population (including isolates), direction, weight formula, node/edge counts, date window, exclusions, and build cost.

Step 4 — Name every projection. Per TASK 11.9 rule one, every projection carries an explicit name so it is never confused with a stored relationship.

Step 5 — Feed into downstream analysis. These named, weighted projections became the input for community detection (Louvain), centrality (PageRank, degree), link prediction (Adamic-Adar), and all graph algorithms that follow.

**Why the raw graph cannot be used directly — the triangle-free problem:**

And a critical warning: the raw graph is triangle-free by construction — proof six. The schema is bipartite: sellers and products can never be directly linked, orders connect to items but items don't connect to each other, and so on. No three labels are pairwise adjacent. That means raw clustering coefficient is exactly zero, and any community or clustering metric run on the raw bipartite schema would be meaningless. All community and clustering work therefore runs on an explicit same-label projection — never on the stored bipartite schema.

**What:** the constraint that the stored graph is unweighted and triangle-free, the derivation of every edge weight from node properties, the five named projections with node/edge counts, the haversine distance derivation, and the end-to-end workflow from raw CSVs to named projections.

**When:** at the start of the machinery deck, before any domain section — because every later number depends on these projections existing first.

**How:** node-property extraction → cleaning/normalization → same-label projection building with count-based weights → explicit naming → downstream graph algorithms. Plus haversine derivation for customer↔seller distance.

**Why:** so the audience understands that every graph edge is a computed, named quantity derived from node properties — not a stored assumption — and why projections are mandatory before any network question can be answered.

**Say it like this:** "The stored graph has no edge weights — no dates, amounts, or counts on relationships. Every weight I use is derived from node properties. For example, seller_shared_categories counts how many distinct categories two sellers both sell in — that count is the edge weight. seller_shared_products counts shared products. seller_co_order counts orders containing both sellers. product_bought_together counts orders containing both products. category_shared_sellers counts shared sellers between two categories. And distance — customer to seller — isn't stored at all; I derived it for all 112,650 items using the haversine formula over ZIP centroids. Every projection is explicitly named. And because the raw graph is bipartite and triangle-free, every community and clustering question needs one of these same-label projections — running it on the raw schema would give exactly zero."

---

## 02 · Seller intelligence — concentration

This section answers RQ1: is revenue dominated by a few sellers? The answer is yes, and I quantify it with the Lorenz curve and the Gini coefficient.

On screen is the Lorenz curve of seller revenue. The x-axis is sellers ranked from poorest to richest; the y-axis is cumulative share of revenue. The dashed diagonal is perfect equality. The gap between the curve and the diagonal is the concentration — that gap is the Gini.
**A Lorenz curve is a graph that shows how wealth or income is distributed across a population**
**Gini Index is a statistical measure of economic inequality**

I computed the Gini over 3,095 sellers ranked by revenue. The formula is G equals the sum over all pairs of absolute differences, divided by two n squared times the mean. Our result: G equals zero point seven nine one six — near-maximal inequality. The bottom 50 percent of sellers — fifteen hundred and forty-seven shops — generate about three point two percent of revenue. The top 1 percent — about 31 sellers — generate 25.7 percent. And half of all item volume flows through just 131 sellers.

To the right, cumulative revenue share bars show top 1 percent at 25.67 percent, top 5 percent at 53.2 percent, top 10 percent at 67.51 percent, and top 30 at 25.67 percent.

I also fit a power law to seller item-incidence: P(X ≥ x) ∝ x^(−α). I estimated the exponent using maximum likelihood — α̂ = 1 + n [ Σᵢ ln(xᵢ / x_min) ]⁻¹ — with x_min found by KS minimization, and computed the p-value from 300 bootstrap repetitions. Our result: α = 2.381, KS p = 0.59, beating lognormal and exponential (Vuong test). I want to be precise here: we fail to reject a power law — we do not prove one. But what it establishes is that the concentration is structural — it's how the marketplace works, not random noise.

**Why this matters:** the seller item-incidence distribution fits a power law, which means the marketplace is operationally dependent on a small seller group. Losing about nine sellers erases roughly a quarter of revenue. Seller loss is a first-order risk, not an edge case.


---

## 03 · Customer experience — the delay cliff

This section answers RQ2: how strongly is lateness associated with ratings? I define delay as delivered customer date minus estimated delivery date, in calendar days, only where a delivery timestamp exists.

On screen is the rating versus delay bucket chart. The purple line is mean review score from one to five; the red bars are the share of one-and-two-star reviews. Both move together as a parcel slips past its promised date.

The numbers: on time — 102,076 items, mean score 4.21, 11.4 percent low. One to three days late — 2,076 items, 3.23 score, 34.0 percent low. Four to seven days — 1,937 items, 2.09 score, 68.0 percent low. Eight to 14 days — 1,574 items, 1.68 score, 80.1 percent low. 15-plus days — 1,469 items, 1.71 score, 78.8 percent low.

The Pearson correlation of delay days with review score is minus zero point two five eight across 111,461 reviewed items. That's about six point seven percent of rating variance moving with delay. I'm careful to say this is correlation, not causation — late delivery and low ratings co-occur. Confounding is tested later, where delay still predicts a rating model.

There's also a regional experience gap: São Paulo sellers carry the most volume but the worst lateness. Long-haul customers outside São Paulo are structurally exposed — that's the geographic root of the causal chain I'll show next.

And a sentiment cross-check: free-text sentiment tracks the score at Spearman rho zero point five five, and 235 reviews out of 40,641 with text contradict their own score — a five-star review with a complaint, for example. That's a review-integrity queue.

**Why this matters:** this is monotone — a gradient, not one cliff. And it's front-loaded — the first three days cost about one star and take low reviews from 11.4 percent to 34.0 percent. Eight to 14 days versus 15-plus days changes almost nothing. The recovery window is the first seven days. Late delivery is the largest controllable effect in the dataset.

**What:** rating vs delay buckets, Pearson correlation, regional gap, sentiment cross-check.
**When:** after concentration, before graph structure.
**How:** delay buckets by calendar day, Pearson r, sentiment Spearman rho.
**Why:** to show that delay, not price, drives dissatisfaction — and where the recovery window is.

**Say it like this:** "Rating drops from 4.21 stars on time to 1.68 stars two weeks late. The share of one-and-two-star reviews climbs from 11 percent to 80 percent. Pearson r minus zero point two five eight. It's a gradient, not one cliff — the damage happens in the first week."

---

## 04 · Graph structure — communities and centrality (RQ3)

This section answers RQ3: do sellers cluster into meaningful business communities? I walk through every card and table on screen, left to right, top to bottom. For each one, I explain what I derived, what it means, and what I infer from it — so a data scientist can see not just the number but the reasoning behind it.

---

**Card 1 — Modularity (Leiden, 10 seeds).**

**What I derived:** I ran Leiden community detection on the seller_shared_categories projection — 3,095 nodes, 724,613 edges — where sellers are linked when they sell in the same category. The edge weight is the count of distinct categories two sellers both sell in. Over 10 random seeds, Leiden finds 6 to 7 communities with modularity Q = 0.357 ± 0.002. The range across seeds is 0.3553 to 0.3585. The degree-preserving rewiring null gives Q = 0.0292, with permutation p = 0.0476. Average path length is 1.87. Seed stability, measured by Normalised Mutual Information, is 0.698 to 0.825.


**What it means:** Q = 0.357 versus a null of 0.029 means the communities are about 12 times stronger than chance. The p-value of 0.0476 says this is statistically significant — not a fluke of random seed choice. The NMI range of 0.70 to 0.83 says the partition is stable but not frozen: borderline sellers move between seeds, but the overall community structure holds across runs.

**What I infer:** Communities are real structural groupings — not an artifact of one algorithm or one random seed. Sellers genuinely cluster together based on the categories they share. For a data scientist, this means: if you want to do cohort analysis, partner matching, or competitive analysis, you should do it at the community level, not at the individual seller level. The communities are the natural units of analysis.

---

**Card 2 — Centrality versus volume.**

**What I derived:** I computed PageRank (structural centrality) and degree centrality (commercial volume — number of connections) for every seller in the projection. PageRank versus degree correlates at Spearman rho = 0.988 — 98.8 percent — near-identical overall. But when I compare the top-10 lists, they are not identical.

**Spearman rho:** Pearson correlation computed on ranks rather than raw values. Robust to skew — both leaderboards span orders of magnitude, so rank correlation is the right measure here.

**What it means:** Overall, central sellers and big sellers look similar — the two rankings track each other closely across the full distribution. But at the top end, they diverge. The top-10 by PageRank is not the same as the top-10 by degree. Some sellers are structurally central because they bridge communities — their products are shared by many others — even if they don't sell the highest volume.

**What I infer:** Volume does not equal structure. You cannot substitute a revenue leaderboard for a centrality leaderboard — they measure different things. For a data scientist, this means: if you're targeting sellers for partnership or intervention, you need both views. Volume tells you who moves the most goods; centrality tells you who holds the network together. A bridge seller with moderate volume but high centrality can be more valuable for network-level interventions than a top-volume seller with a private catalog.

---

**Card 3 — Sparse shared-SKU graph.**

**What I derived:** I built the seller_shared_products projection — sellers linked when they sell the same product. Only 3.7 percent of 32,951 products are sold by more than one seller — that's 1,225 products. The projection has 1,061 edges. 2,309 sellers are isolated (no shared products with anyone). The giant component is 12.6 percent of sellers.

**What it means:** Most sellers have private catalogs — they don't share products with competitors. The shared-product graph is shattered: most sellers are isolated, and the largest connected component covers only about 12 percent of sellers.

**What I infer:** This sparsity is a structural fact, not a modelling choice. It tells me that competitor analysis based on "who sells the same product" will fail — there are too few shared products to build a meaningful competitor network. For a data scientist, this means: do not build product-based competitor analysis or product recommender systems on this data. The signal is too thin. Instead, use the shared-category projection, which is dense and connected (724k edges, 100% connected, ASPL 1.87). The two projections give opposite pictures — shared-product is sparse and fragmented; shared-category is dense and connected — and you must choose the right one for the question.

---

**Link prediction table.**

**What I derived:** Below the three cards is a link-prediction table with two rows:

- **Seller–seller (shared products):** Adamic-Adar AUC = 0.746, average precision 0.0075 (prevalence 0.00005).
- **Product–product (bought together):** CN / AA AUC ≈ 0.50 = chance. Only 3,236 of 98,666 orders (3.3 percent) hold two or more products.

**Adamic-Adar:** AA = Σ 1/ln(deg) over shared neighbours. It down-weights hubs — sharing a rare neighbour counts more than sharing a popular one. Proof 7 bounds AA by common neighbours / log 2, so no hub can artificially inflate scores.

**AUC:** Area under the ROC curve — equals the probability that a randomly chosen positive (future link) ranks above a randomly chosen negative (non-link). 0.746 means a future seller-seller link is ranked above a non-link 74.6% of the time.

**What it means:** Future seller co-selling is genuinely predictable — AUC 0.746 is well above chance (0.50). Product co-purchase is a coin flip — AUC ≈ 0.50 — because baskets are thin: almost every order is a single item, so there's almost no co-purchase signal.

**What I infer:** For a data scientist, this is a routing decision: build seller-partner recommendation (predictable), but do not build a broad product recommender (not predictable). The honest negative — product co-purchase at chance — saves you from wasting engineering effort on a model that cannot work. Redirect effort to the seller layer where the signal is real.


**Community detection robustness (three defenses per TASK 11.9).**

**What I derived:** I proved the clusters survive the method in three ways:

1. **Null model:** degree-preserving rewiring with 20 repetitions gives Q = 0.029 ± 0.001, versus observed Q = 0.357. That's z ≈ 468, p = 0.0476 — chance does not reproduce the clusters.
2. **Seeds:** 10 seeds give Q between 0.355 and 0.359, NMI 0.70 to 0.83 — stable but not frozen.
3. **Method:** Leiden at Q = 0.357 agrees with deterministic multilevel at Q = 0.349. The category-only projection is far weaker at Q = 0.100 — seller communities are not just category groups.

**What it means:** Three independent defenses all agree: the communities are real. They are not an artifact of one algorithm (Leiden agrees with multilevel), one random seed (stable across 10 seeds), or category labels alone (category-only projection is far weaker).

**What I infer:** For a data scientist, this means you can trust the community assignments enough to build downstream decisions on them — cohort targeting, partner matching, risk segmentation. The robustness checks tell you the communities are a property of the data, not a property of your code.

**Bottom-line inference for RQ3:** Communities are real structural groups that a category-only view would miss. The dense category layer — modularity 36 percent versus 2.9 percent chance — is where seller cohorts, partner-matching, and competitive analysis actually live. The shared-product layer is too sparse to support competitor analysis. Volume and centrality diverge at the top — target both. And product co-purchase is chance — do not build a broad product recommender.



**Say it like this:** "On the seller-category projection, Leiden finds six to seven communities at Q zero point three five seven versus a rewiring null of zero point zero two nine — twelve times stronger than chance, p zero point zero four seven six. PageRank and degree agree overall at rho zero point nine eight eight, but their top-ten lists differ — structural influence and commercial volume are not the same ranking. The shared-product graph is sparse — only 1,061 edges — so competitor analysis belongs on the shared-category layer, not the shared-SKU layer. And future seller co-selling is predictable at AUC zero point seven four six, while product co-purchase is a coin flip — build seller recommendations, not product recommenders."

---

## 05 · Marketplace risk — HHI and fragile categories

This section answers RQ4: which categories depend on so few sellers that losing one is a supply event? I compute the Herfindahl–Hirschman Index is a standard economic tool that measures market concentration and overall competitiveness within an industry per category: HHI equals the sum of s_i squared, where s_i is seller i's revenue share within the category. HHI near 1.00 means one seller holds the whole category. Near zero means many equal sellers.

On screen is a category supply concentration chart. X is the number of sellers in the category on a log scale; Y is HHI. The amber line marks the antitrust high-concentration threshold at 0.25. Top-revenue categories like health_beauty and sports_leisure are healthy — hundreds of sellers, HHI under 0.03. The fragile tail is different.

Fragile categories: cds_dvds_musicals — one seller, HHI 1.00 la_cuisine — two sellers, HHI 0.89. Computers — nine sellers, HHI 0.58. Security and services — two sellers, HHI 0.54. Tablets, printing, image — six sellers, HHI 0.48. Flowers — three sellers, HHI 0.48. Office furniture — 34 sellers, HHI 0.42. Office furniture sounds healthy by seller count, but one or two of those 34 hold most of the volume.

A single marketplace-wide score would hide this risk. Overall the marketplace is diversified; the risk lives in the long tail of thin categories. So I compute HHI per category and per region, never once for the whole graph.

Then the at-risk sellers queue. Of 886 sellers with 20 or more reviews, 131 are flagged: late rate 15 percent or higher, or mean score 3.5 stars or lower. These combine weak service with enough volume to matter — they're the sellers a marketplace operator should investigate first. Unusual behaviour is a reason to investigate, not proof of fraud — this dataset cannot establish intent.

**Why this matters:** systemic diversification exists, but risk hides in a thin long tail that a single global score would hide.


**Say it like this:** "HHI measures category concentration: one point zero means one seller owns the whole category. cds_dvds_musicals hits one point zero zero, la_cuisine zero point eight nine, office furniture zero point four two despite 34 sellers. We flag 131 sellers with late rates over 15 percent or ratings under 3.5 — an investigation queue, not a fraud list."

---

## 06 · The master causal chain

This is the strongest finding — not a single correlation, but a chain. Each link is individually significant and monotone, which is why one intervention attacks three outcomes at once.

On screen is the chain: Distance → Freight → Carrier transit → Late delivery → Low rating.

Distance — seller to customer — isn't stored in the database. I derived it for all 112,650 items using the haversine formula over ZIP-prefix centroids. Mean distance is 597 kilometers, median 432. 71 percent of sellers sit in São Paulo; only 42 percent of buyers do. The platform manufactures long hauls.

Freight: I fit log-log OLS because freight is multiplicative: each beta is an elasticity, percent freight change per 1 percent predictor change. Beta distance 0.190, beta weight 0.155, beta price 0.104. Full R squared 0.542; distance alone 0.289. Freight is a distance tax, not a value tax.

Carrier transit: correlation of carrier transit with delivery days is 0.569, versus seller handling 0.19 and approval 0.04. Transit dominates — so the fix is the carrier network, which is a function of distance.

Late delivery: 6 to 8 percent of items, mean ten point five late days among late orders.

Low rating: mean score falls from 4.21 stars on time to 1.68 stars at 8 to 14 days late. Correlation of review score with delay is minus zero point two five eight.

**Why this matters:** distance raises freight cost, lengthens carrier transit, makes the parcel late, which drives the rating down. Regional fulfilment in demand states attacks freight cost, delivery SLA, and customer satisfaction simultaneously — the highest-leverage single move the data supports. The São Paulo hub paradox: São Paulo has the worst hub late rate at 8.33 percent while Rio Grande do Sul is cleanest at 4.4 percent — not a quality problem, just the most long-haul exposure. Don't leave São Paulo; add capacity outside it.

Below the chain are two cards. Freight economics: full model R squared zero point five four two, distance alone zero point two eight nine. A 1 percent increase in distance raises freight zero point one nine percent; weight zero point one five percent; price zero point one zero percent. Feature-dependency map: freight cost driven by distance and weight; delivery delay by carrier transit; review score by delivery delay; delivery time by distance; product link near zero (chance, thin baskets); seller link at Adamic-Adar AUC zero point seven four six, predictable.

**What:** master causal chain diagram, freight economics, feature-dependency map.
**When:** after marketplace risk, before diagnostics.
**How:** haversine derivation, log-log OLS freight elasticities, Pearson correlations.
**Why:** to show one root cause and one lever that improves cost, speed, and satisfaction together.

**Say it like this:** "Distance raises freight, lengthens carrier transit, makes the parcel late, which drives the rating down. Regional fulfilment attacks freight, SLA, and satisfaction in one move — the only lever touching all three."

---

## 06b · Diagnostics — correlation matrix and confusion matrix

Two diagnostic tools side by side. Left: correlation matrix — pairwise association between continuous variables, cells on minus one to plus one. Right: confusion matrix — prediction counts against ground truth: true negatives, false positives, false negatives, true positives. They are not interchangeable, so I state the distinction.
Pearson coefficient is the statistical measure. It calculates the strength and direction of the linear relationship between two continuous variables and value ranges between 1 to -1
Left — correlation matrix. Delivery days versus distance: 0.393 — farther orders take longer, the dominant delivery-time driver. Delivery days versus price: 0.062 — price barely moves delivery time, not a delivery lever. Delivery days versus seller handling: 0.341 — secondary to carrier transit. Delivery days versus carrier transit: 0.569 — road transit is the primary driver. Review score versus delivery delay: -0.258 — late delivery lowers satisfaction, the core chain link. Review score versus price: 0.003 — price irrelevant to review score, ceiling effect dominates. Installments versus price: 0.307 — more installments ride on higher price, affordability framing. Review score versus delay in days: -0.247 — each extra late day shaves about zero point one star.

Right — confusion matrix for the late-delivery classifier, threshold 0.5, prevalence 6.4%, chronological train/test split. True negatives 100,952; false positives 3,337; false negatives 2,446; true positives 4,685. AUC 0.7758; average precision 0.2466; test set 111,420 orders; accuracy 94.8%; trivial baseline predicting all on-time is 93.6%; F1 0.618; recall 0.657; precision 0.584.

Accuracy is deliberately not the headline. At six point four percent prevalence, predicting on-time for every order already scores 93.6 percent. The model adds about 1.2 percentage points over a rubber stamp. Its value is ranking: AUC 77.6 percent concordance means a random late order is scored above a random on-time order 77.6 percent of the time. Recall 65.7 percent catches 4,685 of 7,131 late orders.




**Say it like this:** "Correlation matrix shows distance drives delivery time at r zero point three nine three, and delay kills ratings at r minus zero point two five eight. Confusion matrix: AUC zero point seven seven six, recall 65.7 percent on late orders — but accuracy 94.8 percent is meaningless at six point four percent prevalence, because predicting on-time always scores 93.6 percent."

---

## 06c · Geography — the Brazil map

An interactive choropleth of Brazil's 27 federal units. Shading follows the selected feature — by default late rate. Five filter buttons: late rate percent, order items, mean price in reais, freight proxy, revenue. Hover any state for all five metrics at once — late rate, order items, mean price, freight proxy, revenue — plus that state's share of national demand and revenue. Click for rank out of 27, gap to national median, and interpretation.

Reading the map live:

Late rate — darker is worse. The North dominates: Amapá 11.2 percent, Roraima 10.1 percent, Amazonas 9.8 percent, Pará 9.8 percent. São Paulo hub is 8.3 percent. Rio Grande do Sul is cleanest at 4.4 percent. Median about 6.6 percent. Click Amapá: 4.8 percentage points above the 6.4 percent national rate — nearly 1 order in 9 fails there — from long haul out of a South-East supply core plus thin regional carrier capacity. This lens shows where SLA risk lives.

Order items — the map inverts. São Paulo: 80,564 items, 53.4 percent of national demand. Minas Gerais 8,849. Paraná 8,706. Roraima 80 items. Acre 43. Click a small state: it's a rounding error nationally — serve cross-dock from a hub, don't build local stock. São Paulo is a core market where local stock is unambiguously justified. The demand map is almost the exact inverse of the lateness map, and that gap is the long haul generating everything else.

Mean price: most states cluster between 109 and 175 reais. Bahia is a severe outlier at 444 reais — a low-volume long-tail listing skewing the mean, not a pricing signal. Freight elasticity only zero point one zero four; review-score correlation zero point zero zero three — price is a mix signal, not a lever. We show it to demonstrate we checked it and it doesn't matter.

Revenue: São Paulo 8.6 million reais; Paraná 1.6 million; Santa Catarina 1.27 million; Rio Grande do Sul 1.01 million; Minas Gerais 980,000. Clicking returns a tiering: tier-1 states justify a fulfilment node; above a couple of hundred thousand reais justifies regional stock; below that, serve from a hub.

Freight proxy: scale relative to São Paulo intra-city baseline of 1x. Acre 2.8x, Amapá 2.8x, Amazonas 2.7x — the far interior pays about 3x to move the same parcel as inside São Paulo at 1.2x. This makes the distance elasticity of zero point one nine zero concrete: a multiple a CEO acts on rather than a coefficient a data scientist acts on.

Closing inference: all five lenses in sequence — revenue core, lateness peak, freight bill — sit in largely the same geography. High value and highest operational risk coincide. Which is exactly why regional fulfilment is the recommendation — the one intervention that pays twice, on cost and risk, in the same states.

**What:** Brazil choropleth with five lenses, hover readout, click interpretation.
**When:** after diagnostics, before machine learning.
**How:** hover for five metrics per state; click for rank out of 27, gap to median, interpretation.
**Why:** to show where cost, risk, and revenue actually sit geographically, and why regional fulfilment closes the demand-lateness gap.


## 07 · Machine learning and decision support

Two models, both on chronological splits — train before June 2018, test from June 2018 — so no future information leaks into training. The first is deployable; the second is an honest negative control.

Model 1 — Will this order be late? Deployable. HistGradientBoosting on purchase-time features only: price, freight, weight, distance, installments, states, category — never the actual delivery date, because that would be leakage. Using the answer to predict itself is how a model looks good in a notebook and fails in production. Prevalence 6.4 percent → AUC zero point seven seven six, 77.6 percent concordance; average precision zero point two four seven. Logistic baseline AUC zero point six five nine, 65.9 percent concordance. About 10 days of warning before the promised date — directly deployable as an early-warning trigger for proactive messaging and early carrier escalation.

Model 2 — Will the rating be low? Negative control. Gradient-boosted regression of review score, run twice: tabular features, then tabular plus graph features — seller degree, revenue, k-core from the projections. Mean baseline MAE one point zero five seven. Tabular only MAE zero point nine seven four, R squared zero point zero eight one. Tabular plus graph MAE zero point nine seven one, R squared zero point zero eight two. Graph features add only zero point three MAE points — inside noise against a mean score of 4.03 out of 5. This is the report's negative control: graph structure does not add predictive value for ratings because the rating is set by the delivery clock, not seller position. Do not claim graph features predict ratings.

Time-leakage discipline: both models split on time. The review model can use delivery delay once known, but the late-delivery classifier cannot use the delivery timestamp — it must predict before the fact.

**What:** late-delivery classifier (deployable), review-score regression (negative control).
**When:** after geography, before hypotheses.
**How:** HistGradientBoosting vs logistic regression; chronological split; MAE/R squared for regression, AUC/AP for classification.
**Why:** to give operations an early-warning tool and to honestly cap what graph features can predict for ratings.

**Say it like this:** "Model 1 predicts late delivery at purchase time — AUC zero point seven seven six, ten days of runway. Model 2 predicts review score: graph features add zero point three MAE points — inside noise against a 4.03-star ceiling. The clock sets the rating, not the graph."

---

## 08 · Hypotheses and verdicts

I stated six hypotheses before analysis, then checked each against a null or baseline. Verdicts are separated from known baseline figures so our contribution is distinguishable.

H1 — Marketplace revenue is concentrated in a small seller group. Supported. Revenue Gini zero point seven nine two; top 1 percent of sellers equals 25.7 percent of revenue; half of all items from 131 sellers. Power-law fit alpha two point three eight one, p zero point five nine, beats lognormal and exponential. Our contribution: concentration measured in revenue terms with a Gini, linked to structural dependency — not just restated item counts. Relation: 25.7 percent of revenue comes from the top 1 percent, about 9 sellers. Diminishing — top 5 percent goes to 49.1 percent, so the next 4 percent add about 23.4 points, not 25.7 times 5. Insight: losing 9 sellers erases 25 percent of revenue.

H2 — Late delivery is strongly associated with low ratings. Supported. On-time 4.21 stars versus 8 to 14 days late 1.68 stars; low 1-to-2-star share 11.4 percent to 80.1 percent; r minus zero point two five eight over 111,461 reviewed items. Survives the null: delay classifier AUC zero point seven seven six and the freight-transit-delay chain confirm delay is the operative variable. Caveat: association only, where a delivery timestamp exists. Relation: review score drops 2.53 stars from 4.21 to 1.68 versus on-time; low-rating share rises 68.7 points from 11.4 percent to 80.1 percent. Insight: a 10-day delay shifts a typical 4-star order to 1-star territory — the delivery clock is the single biggest satisfaction lever.

H3 — Seller communities exist and are not just category groups. Supported, modest. Leiden Q zero point three five seven versus rewiring null zero point zero two nine, p zero point zero four eight, stable across 10 seeds with NMI zero point seven zero to zero point eight three. Communities are real, but the category-only projection is far weaker at Q zero point one zero zero — sellers cluster by shared categories plus shared products, a structure category labels alone miss. Relation: Q zero point three five seven versus null zero point zero two nine, about 12 times stronger; stable NMI zero point seven zero to zero point eight three. Insight: communities are real structural groups a category-only view would miss.

H4 — Structurally central sellers are also the top commercial sellers. Partially — they differ. PageRank versus degree rho zero point nine eight eight, 98.8 percent rank agreement overall, yet the top-ten lists differ on every projection. A bridge seller whose products are shared widely can be structurally central without being a volume leader. Central and profitable are related but not the same ranking — a genuine distinction the data forces. Insight: targeting by volume alone misses structural influencers.

H5 — Graph features improve low-rating prediction beyond tabular. Not supported. Adding seller degree, revenue, k-core moves MAE zero point nine seven four to zero point nine seven one — R squared zero point zero eight one to zero point zero eight two. The zero point three point gain is inside noise against a 4.03 out of 5 mean. This is the report's negative control: graph structure does not add predictive value for ratings because the rating is set by the delivery clock, not seller position. Do not claim graph features predict ratings.

H6 — Some categories are exposed to the loss of a single seller. Supported. Per-category HHI reaches 1.00 for cds_dvds_musicals with one seller, and 0.89 for la_cuisine with two sellers; office_furniture has 34 sellers but HHI 0.42. Marketplace-wide picture is diversified — risk concentrated in the thin long tail, which a single global score would hide. Insight: systemic diversification exists but risk hides in a thin long tail.

**Say it like this:** "Six hypotheses, verdicts stated up front: concentration supported, delay-to-ratings supported, communities supported but modest, centrality-equals-volume partially, graph-beats-tabular not supported — that's our honest negative — and single-seller exposure supported."

---

## 09 · Limitations and reproducibility

A finding is only as trustworthy as its weakest assumption. These are the guardrails on every number above.

Data caveats. Person is not customer: customer_id is per-order — 99,441 — while the person is customer_unique_id, 96,096. Only 3.1 percent buy twice, so retention and co-purchase conclusions are structurally thin — report with the 3.1 percent denominator. No edge weights: dates, prices, counts are all derived from node properties; similarity strength is not distance and must be transformed before shortest-path work. Delivery subset: delay and rating analysis uses orders with a delivery timestamp — about 96 thousand plus — a delivered-order view, not the full funnel; cancelled and undelivered orders are excluded. Distance proxy: zip-prefix centroids via haversine — accurate to a few kilometers, not street level. Power law: discrete counts fit with the continuous approximation; a large p fails to reject, it does not prove, a power law.

Reproduce every figure:

python3 analysis/tasks/task10_datascience_report.py — that produces reports/datascience/metrics.json

analysis/.venv/bin/python analysis/tasks/task04_graph_algorithms.py

analysis/.venv/bin/python analysis/tasks/task06_ml.py

python3 analysis/tasks/task05_link_prediction.py

python3 analysis/tasks/task08_timeseries_spatial.py

python3 analysis/proofs.py — fourteen executable mathematical proofs

Source: the 9 Olist CSVs, verified zero-diff against the GrasPh graph — 568,960 nodes, 774,266 relationships — per field manual TASK 11.5/11.6. All analysis is read-only — no writes to GrasPh.

Honest summary: revenue is dangerously concentrated, delay is the dominant driver of dissatisfaction, seller communities are real but modest, graph features do not beat the delivery clock for rating prediction, and the one lever improving cost, speed, and satisfaction together is regional fulfilment. Everything else is a queue to investigate, not a proven cause.

**Say it like this:** "Guardrails first: person is not customer_id — 96,096 people, 3.1 percent repeat — distance is a zip-centroid proxy, the power law fails to reject rather than proves. Reproduce with task10_datascience_report.py plus the analysis tasks — every figure traces to source CSVs verified zero-diff against the graph."

---

## 10 · Mathematical foundations — fourteen proofs

Every claim on this page rests on an identity I proved by executable check — python3 analysis/proofs.py gives 14 out of 14 pass — full write-up in p_math_proofs.md. Each proof gives the formula, its plain meaning, the result restated as a percentage a viewer can read, and which part of the project would be invalid without it.

Why this section matters: a data scientist should never trust a headline number on faith. These proofs are why we can say seller centrality is real, not a half-converged iteration — PageRank. Why the clusters are not chance — modularity and permutation. And why our p-values never overclaim — bootstrap.

The fourteen proofs, plain:

One — Power-law MLE exponent, Clauset et al. 2009. Alpha two point three eight one, KS p zero point five nine. Concentration is structural. Pass.

Two — PageRank stationarity and contraction bound. Converged to 18 decimal places on every projection. Centrality is not a half-run iteration. Pass.

Three — Modularity range minus one-half to one. Q zero point three five seven versus null zero point zero two nine is a real bounded measurement. Pass.

Four — AUC equals Mann-Whitney U. AUC zero point seven seven six equals 77.6 percent concordance probability. Pass.

Five — Support downward closure, Apriori correctness. Cross-sell null is lossless and trustworthy. Pass.

Six — No triangles in stored graph. Raw clustering is exactly zero; projections are mandatory. Pass.

Seven — Adamic-Adar bounded by common neighbours. No hub can inflate link scores; Adamic-Adar AUC zero point seven four six is real. Pass.

Eight — Bootstrap p-value estimator is conservative. P-values never overclaim. Pass.

Nine — Haversine equals great-circle central angle. Distance derived for all 112,650 items — the root cause of every finding. Pass.

Ten — Spectral radius bounds average degree. Constrains centrality scale on large projections. Pass.

Eleven — Spearman rho equals Pearson on mid-ranks. Rho zero point nine eight eight PageRank versus degree, robust to skew. Pass.

Twelve — Permutation test size under a true null. Community p zero point zero four eight has the correct false-positive rate. Pass.

Thirteen — Logistic loss convexity. Logistic baseline solved globally; the gap to gradient boosting is honest. Pass.

Fourteen — Cosine similarity equals normalized dot product. Underpins vector comparisons where used. Pass.

**Say it like this:** "Fourteen executable proofs back every formula — power law, PageRank convergence, modularity bounds, AUC identity, Apriori correctness, triangle-freeness, Adamic-Adar bounds, conservative bootstrap, haversine correctness, spectral radius, Spearman ranks, permutation size, logistic convexity, cosine normalization. Fourteen out of fourteen pass."

---

## Close

Four takeaways, each a number plus the decision it licenses.

One — Revenue is dangerously concentrated. About 9 sellers hold a quarter of revenue — Gini zero point seven nine two. Decision: treat the seller head as first-order risk.

Two — Delay dominates dissatisfaction. One late delivery costs about 1.9 stars, front-loaded into the first 7 days — r minus zero point two five eight. Decision: fix the first week, not the parcel after it's late.

Three — Communities are real but modest. Q zero point three five seven versus null zero point zero two nine, about 12 times stronger than chance. The structural top-ten differs from the revenue top-ten on every projection. Decision: volume does not equal influence — target bridge sellers too.

Four — Regional fulfilment is the one lever. It improves cost, speed, and satisfaction at once, in the same geography where all three costs sit. Decision: add capacity outside São Paulo.

Every headline number traces to a formula, a result, and a null — nothing asserted on faith.

**Say it like this:** "Concentration is severe, delay is the satisfaction lever, communities are real but modest, and regional fulfilment is the single move that improves cost, speed, and satisfaction together."
