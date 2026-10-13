import itertools
import json
import math
import random
import re

from django.test import TestCase

from .algorithms import Graph, run
from .code import code_for


def random_graph(rng, directed, n=None, p=0.3, negative=False, euclid=False):
    n = n or rng.randint(1, 9)
    nodes = [{"id": i + 1, "name": chr(65 + i), "x": rng.uniform(0, 800), "y": rng.uniform(0, 500)} for i in range(n)]
    edges = []
    for a, b in itertools.permutations(range(1, n + 1), 2):
        if not directed and a > b:
            continue
        if rng.random() < p:
            if euclid:  # weight >= straight-line distance / 50 → admissible + consistent heuristic
                (x1, y1), (x2, y2) = [(nodes[i - 1]["x"], nodes[i - 1]["y"]) for i in (a, b)]
                w = max(1, math.ceil(math.hypot(x1 - x2, y1 - y2) / 50)) + rng.randint(0, 3)
            else:
                w = rng.randint(-3 if negative else 1, 9)
            edges.append({"source": a, "target": b, "weight": w})
    return {"directed": directed, "nodes": nodes, "edges": edges}


def floyd(data):
    ids = [n["id"] for n in data["nodes"]]
    d = {(a, b): (0 if a == b else math.inf) for a in ids for b in ids}
    for e in data["edges"]:
        pairs = [(e["source"], e["target"])] + ([] if data["directed"] else [(e["target"], e["source"])])
        for a, b in pairs:
            d[a, b] = min(d[a, b], e["weight"])
    for k in ids:
        for a in ids:
            for b in ids:
                if d[a, k] + d[k, b] < d[a, b]:
                    d[a, b] = d[a, k] + d[k, b]
    return d


def brute_cyclic(data):
    """Directed: some node reaches itself. Undirected: edges >= nodes - components."""
    ids = [n["id"] for n in data["nodes"]]
    if data["directed"]:
        adj = {i: [] for i in ids}
        for e in data["edges"]:
            adj[e["source"]].append(e["target"])
        for s in ids:
            seen, todo = set(), list(adj[s])
            while todo:
                x = todo.pop()
                if x == s:
                    return True
                if x not in seen:
                    seen.add(x)
                    todo += adj[x]
        return False
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for e in data["edges"]:
        a, b = find(e["source"]), find(e["target"])
        if a == b:
            return True
        parent[a] = b
    return False


def tags(code):
    out = set()
    for m in re.finditer(r"#@([\w,]+)", code):
        out |= set(m.group(1).split(","))
    return out


class GraphAlgorithmTests(TestCase):
    def test_against_references(self):
        rng = random.Random(7)
        for _ in range(250):
            directed = rng.random() < 0.5
            data = random_graph(rng, directed, euclid=True)
            g = Graph(directed, data["nodes"], data["edges"])
            ref = floyd(data)
            ids = g.ids
            s, t = rng.choice(ids), rng.choice(ids)

            # cycle check
            res = run(g, "cycle")
            self.assertEqual(res["cyclic"], brute_cyclic(data))
            if res["cyclic"]:
                cyc = res["cycle"]
                self.assertEqual(cyc[0], cyc[-1])
                for a, b in zip(cyc, cyc[1:]):
                    self.assertTrue(any(v == b for v, _ in g.adj[a]))

            # shortest paths
            dj = run(g, "dijkstra", s, t)
            astar = run(g, "astar", s, t)
            bf = run(g, "bellman_ford", s)
            if ref[s, t] == math.inf:
                self.assertFalse(dj["ok"])
                self.assertFalse(astar["ok"])
            else:
                self.assertEqual(dj["outcome"], f"DISTANCE {ref[s, t]:g}")
                self.assertEqual(astar["outcome"], f"DISTANCE {ref[s, t]:g}")
                self.assertAlmostEqual(g.cost(dj["path"]), ref[s, t])
                self.assertAlmostEqual(g.cost(astar["path"]), ref[s, t])
            self.assertTrue(bf["ok"])

            # BFS: fewest edges; DFS / greedy: some valid path
            hops = floyd({**data, "edges": [{**e, "weight": 1} for e in data["edges"]]})
            b = run(g, "bfs", s, t)
            for algo in ("dfs", "greedy"):
                r = run(g, algo, s, t)
                self.assertEqual(r["ok"], ref[s, t] != math.inf, algo)
                if r["ok"]:
                    self.assertEqual(r["path"][0], s)
                    self.assertEqual(r["path"][-1], t)
            if hops[s, t] == math.inf:
                self.assertFalse(b["ok"])
            else:
                self.assertEqual(len(b["path"]) - 1, hops[s, t])

            # topological order
            if directed:
                tp = run(g, "topo")
                self.assertEqual(tp["ok"], not brute_cyclic(data))
                if tp["ok"]:
                    pos = {v: i for i, v in enumerate(tp["order"])}
                    for u, v, _ in g.edges:
                        self.assertLess(pos[u], pos[v])

            # every step points to a line of the shown code
            for algo in ("cycle", "bfs", "dfs", "dijkstra", "greedy", "astar", "bellman_ford") + (("topo",) if directed else ()):
                r = run(g, algo, s, t if algo in ("greedy", "astar", "bfs", "dfs", "dijkstra") else None)
                missing = {st["code"] for st in r["steps"]} - tags(code_for(algo, directed))
                self.assertFalse(missing, (algo, missing))

    def test_negative_cycle(self):
        rng = random.Random(11)
        found = 0
        for _ in range(200):
            data = random_graph(rng, True, negative=True, p=0.35)
            g = Graph(True, data["nodes"], data["edges"])
            s = g.ids[0]
            ref = floyd(data)
            neg_reachable = any(ref[s, v] != math.inf and ref[v, v] < 0 for v in g.ids)
            r = run(g, "bellman_ford", s)
            self.assertEqual(r["ok"], not neg_reachable)
            if not r["ok"]:
                found += 1
                cyc = r["cycle"]
                self.assertEqual(cyc[0], cyc[-1])
        self.assertGreater(found, 5)

    def test_undirected_negative_edge_is_a_negative_cycle(self):
        data = {"directed": False, "nodes": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
                "edges": [{"source": 1, "target": 2, "weight": -1}]}
        g = Graph(False, data["nodes"], data["edges"])
        self.assertEqual(run(g, "bellman_ford", 1)["outcome"], "NEGATIVE CYCLE")


class GraphApiTests(TestCase):
    def post(self, url, body):
        return self.client.post(url, data=json.dumps(body), content_type="application/json")

    def test_analyze(self):
        tri = {"directed": False, "nodes": [{"id": i, "name": n} for i, n in [(1, "A"), (2, "B"), (3, "C")]],
               "edges": [{"source": 1, "target": 2}, {"source": 2, "target": 3}]}
        r = self.post("/api/graph/analyze/", tri).json()
        self.assertFalse(r["cyclic"])
        tri["edges"].append({"source": 3, "target": 1})
        r = self.post("/api/graph/analyze/", tri).json()
        self.assertTrue(r["cyclic"])
        self.assertEqual(len(r["cycle"]), 4)

    def test_errors(self):
        base = {"directed": True, "nodes": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
                "edges": [{"source": 1, "target": 2, "weight": -2}]}
        r = self.post("/api/graph/run/", {**base, "algorithm": "dijkstra", "start": 1})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Bellman-Ford", r.json()["error"])
        r = self.post("/api/graph/run/", {**base, "directed": False, "algorithm": "topo"})
        self.assertEqual(r.status_code, 400)
        r = self.post("/api/graph/run/", {**base, "algorithm": "astar", "start": 1})
        self.assertEqual(r.status_code, 400)  # goal missing
        bad = {**base, "edges": [{"source": 1, "target": 1}]}
        self.assertEqual(self.post("/api/graph/analyze/", bad).status_code, 400)
        dup = {**base, "nodes": [{"id": 1, "name": "A"}, {"id": 2, "name": "a"}]}
        self.assertEqual(self.post("/api/graph/analyze/", dup).status_code, 400)

    def test_run_returns_code_and_ds(self):
        g = {"directed": False, "nodes": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
             "edges": [{"source": 1, "target": 2, "weight": 4}], "algorithm": "dijkstra", "start": 1, "goal": 2}
        r = self.post("/api/graph/run/", g).json()
        self.assertEqual(r["outcome"], "DISTANCE 4")
        self.assertIn("def dijkstra", r["code"])
        self.assertTrue(all("ds" in s for s in r["steps"]))
        self.assertEqual(r["steps"][0]["ds"]["type"], "pq")
