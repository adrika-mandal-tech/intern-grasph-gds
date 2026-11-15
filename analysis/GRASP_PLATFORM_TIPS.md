# Using the GrasPh platform to showcase this work

Two GrasPh surfaces exist. This project uses **both in read-only mode** (no writes, no imports, no
database mutations): the running local server and the hosted web console.

## 1. The hosted web console — `http://100.23.76.198` (admin / admin)

The platform UI confirmed here has these pages (from `/`):

| URL | Purpose for showcasing this work |
|---|---|
| `/query` | The GQL console. Paste any `MATCH` query and see tabular rows instantly. Great for live demos of the "strong" questions — e.g. run the order-status count (`MATCH (o:Order) RETURN o.order_status, count(o)`) and watch it return **delivered 96,478 · shipped 1,107 · canceled 625 · unavailable 609 · invoiced 314**, exactly the manual's numbers. |
| `/explorer` | Interactive graph view. Search a node by id, expand a few hops (Order→OrderItem→Seller→Product→Category), and visually prove **no triangles exist** (Q12): follow Order→Customer→Geolocation→Seller→OrderItem→Order and you hit a dead end at every label — labels never loop back in three hops. |
| `/import` | Upload your own CSV. Showcase answer: export the `seller_shared_categories` projection edges as CSV, import it under a new label, and re-run Leiden in the console to **live-recolor the 6–7 seller communities** you computed offline. |
| `/rag` | Vector search. If you can export the 1,536-d embeddings (task07 P7), push a few product/review vectors here and demo **k-NN "bought-together" nearest neighbors** without training. |
| `/features/admin`, `/features/security`, `/maintenance`, `/observability` | Watch server memory/queries while your projection runs — useful for the "speed report" deliverable. |

### How to run a live query (programmatic, read-only)

```sh
TOK=$(curl -s -X POST http://100.23.76.198/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# server aggregate (safe — single row, not truncated by the 10k row cap)
curl -s -X POST http://100.23.76.198/api/v1/query \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"query":"MATCH (s:Seller)-[:SOLD_BY]->(:OrderItem)-[:ITEM_OF_PRODUCT]->(:Product) RETURN count(DISTINCT s) AS sellers"}'

# a *full* label pull is NOT safe on the hosted box: it caps at 10,000 rows
# and applies the LIMIT before the WHERE filter, so windowed pulls silently
# omit rows. For a faithful cache, use your LOCAL server (TASK 11.6) instead
# and then compare against the hosted aggregate above as the count check.
```

### A live demo script (read-only) for a talk / notebook

```python
from grasph_client import Grasph      # in this repo
g = Grasph(password="admin", url="http://100.23.76.198")   # reads env GRASPH_* if set
print(g.label_counts("olist"))          # {'Order': 99441, 'Customer': 99441, ...}
print(g.query("MATCH (v:Review) RETURN v.review_score AS s, count(v) AS n ORDER BY s"))
print(g.query("MATCH (s:Seller)-[:SOLD_BY]->(i:OrderItem)-[:ITEM_OF_PRODUCT]->(p:Product) "
              "RETURN s.seller_id, count(i) AS items, sum(i.price) AS revenue ORDER BY revenue DESC LIMIT 5"))
```

That last query is **Q2 live**: the top-5 revenue sellers, side by side with the computed
Louvain/Pagerank community table in `analysis/reports/p4_graph_algorithms_summary.md`.

> Note on reliability: during this engagement the hosted `admin/admin` token worked once
> (token received, queries returned correct Olist counts), then later returned
> `InvalidCredentials` on retry — admin sessions appear to expire and the shared demo account
> is **not** a stable backend (the manual warns: *"the demo server is not open to you"*).
> Treat the hosted console as a **spot-check / showcase** tool, not as your analysis backend.
> Your canonical data path is the local dump (TASK 11.6).

## 2. Your LOCAL Grasph server (canonical, raised limits)

```sh
# unpack once
tar -xf olist-grasph-store.tar.xz
export OPENAI_API_KEY="sk-not-a-real-key"      # placeholder; never used for graph queries
# start with raised limits so pulls are not truncated at 10k
bin/graphdb-server-linux --host 0.0.0.0 --port 7474 --admin-password olist-local-1 \
  --data-dir grasph-data --native-data-dir grasph-data/native-data \
  --query-timeout-secs 3600 --max-path-bindings 5000000 \
  --max-result-rows 5000000 --max-materialized-bindings 5000000
# probe
GRASPH_PASSWORD=olist-local-1 python3 grasph_client.py   # expect 568,960 nodes / 774,266 rels
```

**Showcase move — verify a projection live against the server (TASK 11.9 rule 6):**
run the example query for the seller–revenue leaderboard and compare it to the same
number you compute offline from the pulled tables. If they differ, the error is in the pull,
not the algorithm — that is the point of the rule.

Then, for a talk, switch to `/import` and load your computed projection CSVs:
`category_shared_sellers_edges.csv`, `seller_shared_categories_edges.csv`, the Leiden
membership you found, and the PageRank/hits scores from `p4_graph_algorithms.json`.
The audience sees your offline communities re-drawn and re-colored inside Grasph, and can
hover to read each seller's degree, revenue and k-core — the exact same numbers from
`reports/SYNTHESIS.md`.

## 3. Turning results into a 5-minute showcase

1. Open `/query`. Paste the order-status count → "this is the real Olist dataset".
2. Open `/explorer`. Show the bipartite schema (Order→OrderItem→Seller/Product→Category), and
   expand one order to reveal only **two** hop paths — then state **Q12: zero triangles**,
   pointing at `analysis/proofs.py` proof 6 for the structural argument (not just a measured 0).
3. Switch to `/import`, load `seller_shared_categories_edges.csv` (724,613 edges) as a new
   graph, run the platform's own community detection → "6–7 clusters, modularity 0.356,
   matching my offline Leiden — see the null-model z-score in `p4_graph_algorithms.json`."
4. `/rag`: drop a product id, retrieve its 3 nearest products by the stored 1,536-d vector —
   "bought-together without training" — and cross-read the AP lift from `p5_link_prediction.json`.
5. `/query` again: the freight-vs-distance correlation (Q3) — pull one order with a long zip
   distance and show the high freight, then show the regression β = 0.190 (distance), 0.155
   (weight) from `p8_timeseries_spatial_summary.md`.

This stitches every phase (profiling → projection → algorithm → prediction → NLP → space) to a
single live screen, each claim backed by a `reports/` artifact and the `proofs.py` math.
