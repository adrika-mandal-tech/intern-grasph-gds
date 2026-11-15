"""A small client for a Grasph server: log in, run a query, pull whole labels and relationship types.

Grasph has no bolt driver. A program talks to it over HTTP:
    POST /api/v1/auth/login   {"username", "password"}  ->  {"token"}
    POST /api/v1/query        {"query": "<GQL or Cypher>"}  ->  {"columns", "rows", "row_count", "truncated"}

    from grasph_client import Grasph
    g = Grasph()                                   # http://127.0.0.1:7474, admin / admin
    g.query("MATCH (s:Seller) RETURN count(s)")    # {'columns': ['count'], 'rows': [[3095]], ...}
    sellers = g.nodes("Seller")                    # list of dicts, one per node, vectors left out
    sold_by = g.rels("SOLD_BY")                    # list of dicts: id, from, to, properties

Only the Python standard library is needed. Run this file to print the counts of the server:
    python grasph_client.py
"""
import json
import os
import urllib.error
import urllib.request

# Properties that hold an embedding vector: about 20 KB of text on each node that has one.
VECTOR_KEYS = {"entity_vector", "embedding", "vector"}


class Truncated(Exception):
    """The server cut the result short. Start it with the limits raised (see the manual, TASK 11.6)."""


class Grasph:
    def __init__(self, base=None, user=None, password=None):
        self.base = base or os.environ.get("GRASPH_URL", "http://127.0.0.1:7474")
        self.token = None
        reply = self._call("POST", "/api/v1/auth/login", {
            "username": user or os.environ.get("GRASPH_USER", "admin"),
            "password": password or os.environ.get("GRASPH_PASSWORD", "admin")})
        self.token = reply["token"]

    def _call(self, method, path, body=None, timeout=3600):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:500]}") from None

    def query(self, gql, allow_truncated=False):
        """Run one query. The reply has `columns`, `rows` and `row_count`.

        A reply the server cut short raises `Truncated`, because a short result looks
        like a complete one. Pass allow_truncated=True when a partial result is what you want.
        """
        reply = self._call("POST", "/api/v1/query", {"query": gql})
        if reply.get("truncated") and not allow_truncated:
            raise Truncated(f"{reply.get('truncation_reason')}: {reply['row_count']} rows returned for: {gql}")
        return reply

    def status(self):
        """Total nodes and relationships in the store."""
        return self._call("GET", "/api/v1/native/status")

    def schema(self, namespace):
        """The saved schema of a namespace: labels, properties, relationship types and their key columns."""
        return self._call("GET", f"/api/v1/ingest/schema/{namespace}")

    def label_counts(self, namespace):
        """Node count of each label in the namespace's schema. One query per label:
        a single query over every node of the store holds them all in server memory."""
        labels = [n["label"] for n in self.schema(namespace)["node_schemas"]]
        return {label: self.query(f"MATCH (n:{label}) RETURN count(n)")["rows"][0][0] for label in labels}

    def rel_type_counts(self, namespace):
        """Relationship count of each type in the namespace's schema. Slow: about a minute per type."""
        out = {}
        for r in self.schema(namespace)["rel_schemas"]:
            query = f"MATCH (a:{r['from_label']})-[r:{r['rel_type']}]->(b:{r['to_label']}) RETURN count(r)"
            out[r["rel_type"]] = self.query(query)["rows"][0][0]
        return out

    def property_keys(self, label, sample=200):
        """Property names seen on a sample of nodes of one label, vector properties left out."""
        keys = set()
        for (node,) in self.query(f"MATCH (n:{label}) RETURN n LIMIT {sample}")["rows"]:
            keys.update(node["properties"])
        return sorted(keys - VECTOR_KEYS)

    def nodes(self, label, properties=None):
        """Every node of one label as a dict: `_id` (the node id) and one entry per property.

        The properties are asked for by name, so the vectors never travel.
        """
        properties = properties or self.property_keys(label)
        rows = self.query(f"MATCH (n:{label}) RETURN id(n), " + ", ".join(f"n.{p}" for p in properties))["rows"]
        return [dict(zip(["_id"] + list(properties), row)) for row in rows]

    def rels(self, rel_type):
        """Every relationship of one type as a dict: `id`, `from`, `to` (node ids), `properties`."""
        rows = self.query(f"MATCH ()-[r:{rel_type}]->() RETURN r")["rows"]
        return [{"id": r["id"], "from": r["from"], "to": r["to"], "properties": r.get("properties") or {}} for (r,) in rows]


if __name__ == "__main__":
    g = Grasph()
    print("server:", g.base, g.status())
    for label, n in sorted(g.label_counts("olist").items()):
        print(f"  {label:18s}{n:>10,}")
