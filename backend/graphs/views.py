"""Graph API (stateless: the frontend sends the whole graph every time).

POST /api/graph/analyze/  {"directed", "nodes", "edges"}
     -> {"cyclic", "cycle", "cycle_text", "negative_edges"}         (quick, no steps)
POST /api/graph/run/      {"directed", "nodes", "edges", "algorithm", "start"?, "goal"?}
     -> {"algorithm", "ok", "outcome", "steps", "code", ...}

nodes: [{"id": 1, "name": "A", "x": 100, "y": 200}]   (x, y are used by the A* / greedy heuristic)
edges: [{"source": 1, "target": 2, "weight": 3}]
"""
from config.api import BadRequest, api_view

from .algorithms import ALGORITHMS, Graph, GraphError, cycle_check, run
from .code import code_for


def _graph(data: dict) -> Graph:
    try:
        return Graph(data.get("directed", False), data.get("nodes", []), data.get("edges", []))
    except GraphError as e:
        raise BadRequest(str(e))


@api_view()
def analyze(request, data):
    g = _graph(data)
    res = cycle_check(g, with_steps=False)
    cyc = res["cycle"]
    return {
        "cyclic": res["cyclic"],
        "cycle": cyc,
        "cycle_edges": g.pairs(cyc),
        "cycle_text": res.get("cycle_text", ""),
        "negative_edges": any(w < 0 for _, _, w in g.edges),
    }


@api_view()
def run_algorithm(request, data):
    g = _graph(data)
    algorithm = data.get("algorithm")
    try:
        result = run(g, algorithm, data.get("start"), data.get("goal"))
    except GraphError as e:
        raise BadRequest(str(e))
    return {
        "algorithm": algorithm,
        "title": ALGORITHMS[algorithm][0],
        "code": code_for(algorithm, g.directed),
        **result,
    }
