# GrasPh Visualisation Opportunities + a CrispDM Delivery Plan

**Purpose.** The three HTML reports are static/one-off artefacts. This document identifies the
visualisations that can be produced *inside GrasPh itself* so the analysis is live, and maps them to
the **CRISP-DM** methodology (Cross-Industry Standard Process for Data Mining) so the board sees a
recognisable data-science process rather than "some charts."

**Environment:** hosted console `http://100.23.76.198/` (admin). Modules available in the left nav:
Dashboard · Graph Explorer · Query Editor · RAG Pipeline · Import/Export · Maintenance · Observability.

---

## Part 1 — What GrasPh can render natively

| Module | What it renders | Best used for here |
|---|---|---|
| **Graph Explorer** | Node-and-edge canvas; expand a node's neighbours; style by label/colour/size; schema view; tabular data view | The 9 projections, community partitions, at-risk seller neighbourhoods, the customer↔seller distance edge |
| **Query Editor** | Run a GQL query → result set as table; results can be pushed onto the canvas | Every aggregate: late rate by state, freight by distance band, HHI by category, AUC-supporting distributions |
| **Dashboard** | Saved panels of repeated queries — aggregate/monitoring views | The operational KPIs: lateness rate, freight cost per km, flagged-seller count, review trend |
| **Observability** | Query/runtime telemetry | Not for the deck; useful to prove a number came from an uncapped pull |
| **Import / Export** | Load and extract graph data | Re-import derived edge weights (e.g. distance) as an edge property so Graph Explorer can size by it |
| **RAG Pipeline** | Retrieval over graph content | Not a visualisation target for the board |

**Key capability to exploit:** Graph Explorer styles nodes by property. If we **import the derived
distance, freight and late-rate values as edge/node properties**, then node *size* and *colour* in the
Explorer become the visual encoding — no external charting library needed, and it stays live against
the graph.

---

## Part 2 — 12 visualisations, ranked by board impact

### Tier 1 — build these first (each answers one RQ)

**V1 · The master chain, live.** Graph Explorer, canvas view. Colour nodes by phase of the chain:
distance-derived edges in orange, freight-bearing nodes in amber, late parcels in red, low-rated
orders in purple. GraPh preserves whatever styling you set, so the causal chain becomes a *rendering
rule* you can re-apply per seller.
*Why it works:* the board sees cost, SLA and satisfaction as one topology rather than three slides.

**V2 · Distance-vs-outcome, colour-encoded.** Import the haversine distance as a `dist_km` edge
property, then in Graph Explorer set node size ∝ distance and colour ∝ late-flag. The long hauls
literally light up red and grow.
*Why it works:* it is the elasticity β = 0.190 made visible without a scatter plot.

**V3 · Late rate by state (query → table → choropleth substitute).**
```gql
MATCH (o:Order)-[:PLACED_BY]->(c:Customer)-[:CUSTOMER_LOCATED_IN]->(g:Geolocation)
WHERE o.order_delivered_customer_date > o.order_estimated_delivery_date
RETURN g.geolocation_state AS state, count(o) AS late_orders,
       round(100.0*count(o)/41436, 2) AS late_rate_pct
ORDER BY late_orders DESC LIMIT 27
```
*Render as:* a saved Dashboard panel (bar) **and** the interactive map already in `Datascience.html`.
*Why both:* GrasPh gives the queryable truth; the HTML map gives the clickable interpretation.

**V4 · Lorenz curve for seller concentration.** The Lorenz points are already computed
(`M.conc.lorenz` in Datascience.html). In GrasPh, run a cumulative-share query and plot in the Query
Editor result pane; keep the HTML curve for the presentation because GrasPh's Query Editor does not
draw curves.
*Honest limitation:* GrasPh is a **graph** platform — it renders nodes, edges, tables and aggregates,
not continuous curves. Where a chart must be a curve (Lorenz, dose-response, ROC), the HTML page is
the correct home.

**V5 · Seller-revenue concentration as a size-encoded graph.** Query top-N sellers by revenue, push
onto the canvas, size nodes by revenue. The top-1% visually dwarfs the rest — a Gini of 0.792 becomes
obvious in one screenshot.

### Tier 2 — the fragility and structure story (RQ3, RQ4)

**V6 · Community partition rendered.** Push the seller×shared-category projection into the Explorer
and colour each node by its Leiden community id. Communities become visually distinct blocks — Q 0.357
made visible, and you can click into one to show a bridge seller.

**V7 · Bridge-seller contrast.** Two canvas views side by side: nodes sized by **degree** vs nodes
sized by **PageRank**. The top-10 lists differ on every projection, so the two screenshots disagree
in exactly the way ρ = 0.988 conceals. *This is the single best "structure ≠ volume" exhibit.*

**V8 · Fragile-category subgraph.** Filter to one category (e.g. `cds_dvds_musicals`, HHI 1.00) and
render its seller set — a single node. Then `office_furniture` with 34 sellers, HHI 0.42, sized by
share. The visual contrast *is* the HHI argument.

**V9 · At-risk seller queue.** Colour nodes red where derived late-rate ≥ 15% or mean score ≤ 3.5★.
131 of 886 sellers light up. Clicking one expands its orders — the "investigate, not fraud" exhibit,
because you can show the evidence trail per seller.

### Tier 3 — operational monitoring

**V10 · Lateness KPI dashboard.** Saved panels: late rate (current), late rate by state, late rate by
week, count of flagged sellers. This is what a marketplace ops team would actually watch.

**V11 · Freight-per-km monitor.** Panel of mean freight by distance band (the R$12.65 → R$43.95
sequence) — the direct operational readout of the 0.190 elasticity.

**V12 · Review-integrity queue.** Colour review nodes where sentiment and star rating disagree. 235
nodes — a concrete QA worklist straight out of the graph.

---

## Part 3 — CRISP-DM mapping

CRISP-DM has six phases. Mapping the project onto them is what makes it legible as data *mining*
rather than dashboarding, and it gives you a slide structure that a board or an assessor recognises.

| CRISP-DM phase | What we did | Visual to show |
|---|---|---|
| **1. Business Understanding** | State the objective: freight cost, delivery SLA and satisfaction are all suspect; identify RQ1–RQ5 | Framing slide — 5 RQs with verdicts |
| **2. Data Understanding** | 41-check profile of the source CSVs; 0-different verification against the stored graph; discovery of the 4 near-empty boundary months; discovery that the schema is bipartite and triangle-free | The verification table + the boundary-month callout |
| **3. Data Preparation** | **9 named projections** to make the bipartite schema clusterable; derive the haversine distance edge; derive all edge weights from node properties (none is stored); restrict to the 20-month window; zfill zip codes | The projection flowchart (FIG A, Stage B) |
| **4. Modelling** | Power-law fit (α 2.381); Leiden modularity (Q 0.357 vs 0.029 null); PageRank/degree/k-core/components/ASPL; 4 link-prediction heuristics (AA AUC 0.746); gradient-boosted lateness classifier (AUC 0.7758 vs logistic 0.6593); gradient-boosted rating model (R² 0.081) | Communities canvas, bridge-seller contrast, at-risk queue |
| **5. Evaluation** | **14 executable proofs**; null/baseline for every headline number (rewiring null, KS p, trivial 93.6% accuracy baseline); **deliberate negative control** on graph features (RQ5); stated limitations | The 14-proofs table; the honest summary callout |
| **6. Deployment** | The intervention: **regional fulfilment**, the only lever moving cost + SLA + satisfaction together; plus 5 operational queues (anomalies, at-risk sellers, review-integrity, fragile categories, freight bands) | The Brazil map; the master chain; the ops queue list |

**Why this framing matters commercially:** CRISP-DM phase 5 (Evaluation) is where most analytics
projects quietly skip the nulls and the negative controls. Ours is the most populated phase in the
whole project — 14 proofs and 3 explicit negatives — which is the strongest single credibility claim
available.

---

## Part 4 — Recommended build order

1. **Import the derived properties** (distance, freight, late-flag, community id) as node/edge
   properties via Import/Export. This is the one prerequisite — without it the Explorer cannot encode
   anything by size or colour.
2. **Build V1 (master chain) and V7 (bridge-seller contrast)** — these two are the deck's spine and
   are pure Graph Explorer work, no charting library needed.
3. **Build V3 + V10 (late-rate table and KPI dashboard)** as saved Query Editor panels.
4. **Build V6 and V9** (communities, at-risk queue) for the RQ3/RQ4 section.
5. **Leave V4/V2 chart-type gaps to the HTML pages**, and say so: GrasPh renders topology and
   aggregates; curves belong in the report pages. Being explicit about the division of labour is more
   credible than claiming GrasPh does everything.

**One honest caveat to state in the room:** the hosted console's authentication is intermittent, so
any live demo should be rehearsed against the **local server with raised row limits**, and every
pulled count cross-checked against the server's own count before it goes on a slide.

---

## Appendix — CRISP-DM in one line per phase

Business Understanding: *why* are freight, lateness and ratings all under suspicion?
Data Understanding: *what* is actually in these 9 CSVs, and does the graph match?
Data Preparation: *how* do we make a triangle-free bipartite schema answerable?
Modelling: *which* algorithms, and against which null?
Evaluation: *how do we know* — 14 proofs, 3 negatives, stated limits.
Deployment: *what changes* on Monday — regional fulfilment plus 5 queues.
