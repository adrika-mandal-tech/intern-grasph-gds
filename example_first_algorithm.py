"""One worked example of the path from Grasph to a graph algorithm. It is a starting point, not a result.

    pip install networkx
    python example_first_algorithm.py

With Neo4j you wrote:
    CALL gds.graph.project('g', ['Product', 'ProductCategory'], {IN_CATEGORY: {orientation: 'UNDIRECTED'}})
    CALL gds.degree.stream('g') YIELD nodeId, score
Grasph has no GDS library today. So the three steps happen in your program:
    1. pull the relationships out of Grasph,
    2. build the projected graph in a graph library,
    3. run the algorithm there.
"""
import networkx as nx

from grasph_client import Grasph

g = Grasph()

# 1. Pull. One relationship type and the label that gives the nodes a readable name.
in_category = g.rels("IN_CATEGORY")                                  # Product -> ProductCategory
categories = {c["_id"]: c["product_category_name_english"] for c in g.nodes("ProductCategory")}

# 2. Project. An undirected graph of the two labels at the ends of IN_CATEGORY.
graph = nx.Graph()
graph.add_edges_from((r["from"], r["to"]) for r in in_category)
print(f"projected graph: {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges")

# 3. Run. Degree of each category = number of products in it.
degree = {node: d for node, d in graph.degree() if node in categories}
for node, d in sorted(degree.items(), key=lambda kv: -kv[1])[:5]:
    print(f"  {categories[node]:24s}{d:>6,}")

# The same number from Grasph itself, as a check that the pull and the projection are right:
check = g.query("MATCH (p:Product)-[:IN_CATEGORY]->(c:ProductCategory) "
                "RETURN c.product_category_name_english AS category, count(p) AS products ORDER BY products DESC LIMIT 5")
print("the same from a query:", check["rows"])
