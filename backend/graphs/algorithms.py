"""Graph algorithms with step-by-step output.

Every algorithm returns a list of steps. A step is:
    {
      "message":  what happens now (English),
      "status":   info | found | not_found | done,
      "code":     tag of the Python line that runs (see code.py),
      "highlight": {current, visited, frontier, active_edge, path_nodes, path_edges,
                    cycle_nodes, cycle_edges, labels},
      "ds":       the helper data structure right now
                  {"type": "queue"|"stack"|"pq"|"table", "title", "items": [{label, detail?, stale?}], "active"?}
    }
Nodes are referred to by their integer id; edges as [u, v] pairs.
"""
from __future__ import annotations

import heapq
import math
from typing import Any, Optional

INF = math.inf
H_SCALE = 50  # screen pixels per 1 unit of distance for the A* / greedy heuristic


class GraphError(ValueError):
    """Bad input (shown to the user as a 400 error)."""


def _num(x: float) -> str:
    if x == INF:
        return "∞"
    if x == -INF:
        return "-∞"
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


class Graph:
    MAX_NODES = 60
    MAX_EDGES = 400

    def __init__(self, directed: bool, nodes: Any, edges: Any) -> None:
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise GraphError("'nodes' and 'edges' must be lists.")
        if len(nodes) > self.MAX_NODES or len(edges) > self.MAX_EDGES:
            raise GraphError(f"At most {self.MAX_NODES} nodes and {self.MAX_EDGES} edges.")
        self.directed = bool(directed)
        self.ids: list[int] = []
        self.names: dict[int, str] = {}
        self.pos: dict[int, tuple[float, float]] = {}
        seen_names: set[str] = set()
        for n in nodes:
            if not isinstance(n, dict):
                raise GraphError("Each node must be an object.")
            nid, name = n.get("id"), n.get("name")
            if isinstance(nid, bool) or not isinstance(nid, int) or nid in self.names:
                raise GraphError("Every node needs a unique integer 'id'.")
            if not isinstance(name, str) or not name.strip():
                raise GraphError("Every node needs a name.")
            name = name.strip()
            if name.lower() in seen_names:
                raise GraphError(f"Two nodes are called '{name}'.")
            seen_names.add(name.lower())
            x, y = n.get("x", 0), n.get("y", 0)
            if not all(isinstance(c, (int, float)) and math.isfinite(c) for c in (x, y)):
                raise GraphError("Node coordinates must be numbers.")
            self.ids.append(nid)
            self.names[nid] = name
            self.pos[nid] = (float(x), float(y))

        self.edges: list[tuple[int, int, float]] = []  # as entered
        self.adj: dict[int, list[tuple[int, float]]] = {i: [] for i in self.ids}
        seen_edges: set[tuple[int, int]] = set()
        for e in edges:
            if not isinstance(e, dict):
                raise GraphError("Each edge must be an object.")
            u, v, w = e.get("source"), e.get("target"), e.get("weight", 1)
            if u not in self.names or v not in self.names:
                raise GraphError("An edge points to a node that does not exist.")
            if u == v:
                raise GraphError("Self-loops are not supported.")
            if isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or abs(w) > 1e6:
                raise GraphError("Edge weights must be numbers.")
            key = (u, v) if self.directed else (min(u, v), max(u, v))
            if key in seen_edges:
                continue  # ignore duplicates
            seen_edges.add(key)
            self.edges.append((u, v, float(w)))
            self.adj[u].append((v, float(w)))
            if not self.directed:
                self.adj[v].append((u, float(w)))
        for i in self.ids:  # deterministic order: neighbours by name
            self.adj[i].sort(key=lambda t: self.names[t[0]].lower())

    # ---------------------------------------------------------------- helpers
    def n(self, i: int) -> str:
        return self.names[i]

    def arrow(self) -> str:
        return "→" if self.directed else "—"

    def e(self, u: int, v: int) -> str:
        return f"{self.n(u)} {self.arrow()} {self.n(v)}"

    def node_id(self, v: Any, what: str) -> int:
        if v not in self.names:
            raise GraphError(f"Choose a {what} node.")
        return v

    def h(self, a: int, b: int) -> float:
        """Straight-line distance on screen / H_SCALE, rounded down to 1 decimal (never overestimates)."""
        (x1, y1), (x2, y2) = self.pos[a], self.pos[b]
        return math.floor(math.hypot(x1 - x2, y1 - y2) / H_SCALE * 10) / 10

    def directed_edges(self) -> list[tuple[int, int, float]]:
        """Each undirected edge counts in both directions."""
        if self.directed:
            return list(self.edges)
        out = []
        for u, v, w in self.edges:
            out += [(u, v, w), (v, u, w)]
        return out

    def path(self, prev: dict[int, Optional[int]], goal: int) -> list[int]:
        p, cur = [], goal
        while cur is not None:
            p.append(cur)
            cur = prev.get(cur)
        return p[::-1]

    @staticmethod
    def pairs(nodes: list[int]) -> list[list[int]]:
        return [[a, b] for a, b in zip(nodes, nodes[1:])]

    def names_of(self, ids: list[int]) -> str:
        return ", ".join(self.n(i) for i in ids)

    def path_text(self, ids: list[int]) -> str:
        return f" {self.arrow()} ".join(self.n(i) for i in ids)

    def cost(self, ids: list[int]) -> float:
        total = 0.0
        for a, b in zip(ids, ids[1:]):
            total += min(w for v, w in self.adj[a] if v == b)
        return total

    @staticmethod
    def step(message: str, code: str, status: str = "info", ds: Optional[dict] = None, **hl: Any) -> dict:
        s = {
            "message": message,
            "status": status,
            "code": code,
            "highlight": {k: v for k, v in hl.items() if v is not None},
        }
        if ds is not None:
            s["ds"] = ds
        return s


def _queue(g: Graph, items: list[int], title: str = "Queue (front → back)", details: Optional[dict] = None, active: Optional[int] = None) -> dict:
    d = {"type": "queue", "title": title, "items": [{"label": g.n(i), **({"detail": details[i]} if details and i in details else {})} for i in items]}
    if active is not None:
        d["active"] = active
    return d


def _stack(g: Graph, items: list[str], title: str, active: Optional[int] = None) -> dict:
    d = {"type": "stack", "title": title, "items": [{"label": s} for s in items]}
    if active is not None:
        d["active"] = active
    return d


def _pq(g: Graph, heap: list[tuple], stale: set[int], title: str, fmt_prio=_num, active_top: bool = False) -> dict:
    """Priority queue, shown sorted by priority (smallest first)."""
    entries = sorted(heap)
    items = []
    for entry in entries:
        prio, node = entry[0], entry[-1]
        item = {"label": g.n(node), "detail": fmt_prio(prio)}
        if (node, prio) in stale or node in stale:
            item["stale"] = True
        items.append(item)
    d = {"type": "pq", "title": title, "items": items}
    if active_top and items:
        d["active"] = 0
    return d


def _dist_labels(g: Graph, dist: dict[int, float]) -> dict[int, str]:
    return {i: _num(dist.get(i, INF)) for i in g.ids}


def _table(g: Graph, dist: dict[int, float], prev: dict[int, Optional[int]], title: str, active: Optional[int] = None) -> dict:
    items = []
    for idx, i in enumerate(g.ids):
        via = prev.get(i)
        items.append({"label": g.n(i), "detail": f"{_num(dist[i])}" + (f"  (via {g.n(via)})" if via is not None else "")})
    d = {"type": "table", "title": title, "items": items}
    if active is not None:
        d["active"] = g.ids.index(active)
    return d


# =================================================================== BFS
def bfs(g: Graph, start: int, goal: Optional[int]) -> dict:
    steps: list[dict] = []
    visited = [start]
    parent: dict[int, Optional[int]] = {start: None}
    level = {start: 0}
    queue = [start]
    order: list[int] = []

    def labels():
        return {i: f"d={level[i]}" for i in level}

    steps.append(g.step(
        f"Start at {g.n(start)}: mark it visited and put it in the queue. "
        "BFS explores the graph level by level (by number of edges).",
        "init", current=start, visited=list(visited), frontier=list(queue), labels=labels(), ds=_queue(g, queue),
    ))
    while queue:
        node = queue[0]
        steps.append(g.step(
            f"Take {g.n(node)} from the front of the queue.", "pop",
            current=node, visited=list(visited), frontier=list(queue), labels=labels(), ds=_queue(g, queue, active=0),
        ))
        queue.pop(0)
        order.append(node)
        if node == goal:
            p = g.path(parent, goal)
            steps.append(g.step(
                f"{g.n(goal)} reached! Path with the fewest edges: {g.path_text(p)} ({len(p) - 1} edge(s)).",
                "found", status="found", current=node, visited=list(visited), path_nodes=p, path_edges=g.pairs(p),
                labels=labels(), ds=_queue(g, queue),
            ))
            return {"ok": True, "outcome": f"FOUND · {len(p) - 1} EDGE(S)", "steps": steps, "path": p}
        for nb, _ in g.adj[node]:
            if nb in level:
                steps.append(g.step(
                    f"Edge {g.e(node, nb)}: {g.n(nb)} was already visited → skip.", "skip",
                    current=node, active_edge=[node, nb], visited=list(visited), frontier=list(queue),
                    labels=labels(), ds=_queue(g, queue),
                ))
                continue
            visited.append(nb)
            parent[nb] = node
            level[nb] = level[node] + 1
            queue.append(nb)
            steps.append(g.step(
                f"Edge {g.e(node, nb)}: {g.n(nb)} is new → mark it visited (distance {level[nb]}) "
                f"and add it to the back of the queue.",
                "push", current=node, active_edge=[node, nb], visited=list(visited), frontier=list(queue),
                labels=labels(), ds=_queue(g, queue, active=len(queue) - 1),
            ))
    if goal is not None:
        steps.append(g.step(
            f"The queue is empty and {g.n(goal)} was never reached → there is no path from {g.n(start)}.",
            "done", status="not_found", visited=list(visited), labels=labels(), ds=_queue(g, []),
        ))
        return {"ok": False, "outcome": "NOT REACHABLE", "steps": steps}
    steps.append(g.step(
        f"The queue is empty → BFS is finished. Visit order: {g.names_of(order)}.",
        "done", status="found", visited=list(visited), labels=labels(), ds=_queue(g, []),
        path_edges=[[parent[i], i] for i in order if parent[i] is not None],
    ))
    return {"ok": True, "outcome": f"VISITED {len(order)} NODES", "steps": steps}


# =================================================================== DFS
def dfs(g: Graph, start: int, goal: Optional[int]) -> dict:
    steps: list[dict] = []
    stack: list[int] = [start]
    visited: list[int] = []
    parent: dict[int, Optional[int]] = {start: None}

    def ds(active=None):
        # shown with the top of the stack first
        return _stack(g, [g.n(i) for i in reversed(stack)], "Stack (top first)", active)

    steps.append(g.step(
        f"Put {g.n(start)} on the stack. DFS always continues from the most recently found node, "
        "going as deep as possible before backtracking.",
        "init", current=start, frontier=list(stack), ds=ds(),
    ))
    while stack:
        steps.append(g.step(
            f"Pop {g.n(stack[-1])} from the top of the stack.", "pop",
            current=stack[-1], visited=list(visited), frontier=list(stack), ds=ds(active=0),
        ))
        node = stack.pop()
        if node in visited:
            steps.append(g.step(
                f"{g.n(node)} was already visited → ignore this stack entry.", "skip",
                current=node, visited=list(visited), frontier=list(stack), ds=ds(),
            ))
            continue
        visited.append(node)
        tree_edges = [[parent[i], i] for i in visited if parent.get(i) is not None]
        steps.append(g.step(
            f"Visit {g.n(node)} (number {len(visited)} in the DFS order).", "visit",
            current=node, visited=list(visited), frontier=list(stack), path_edges=tree_edges, ds=ds(),
        ))
        if node == goal:
            p = g.path(parent, goal)
            steps.append(g.step(
                f"{g.n(goal)} reached! DFS path: {g.path_text(p)} (DFS finds a path, not necessarily the shortest).",
                "found", status="found", current=node, visited=list(visited), path_nodes=p, path_edges=g.pairs(p), ds=ds(),
            ))
            return {"ok": True, "outcome": f"FOUND · {len(p) - 1} EDGE(S)", "steps": steps, "path": p}
        # push in reverse so the alphabetically first neighbour is on top
        for nb, _ in reversed(g.adj[node]):
            if nb in visited:
                continue
            parent[nb] = node
            stack.append(nb)
            steps.append(g.step(
                f"Edge {g.e(node, nb)}: {g.n(nb)} not visited yet → push it on the stack.", "push",
                current=node, active_edge=[node, nb], visited=list(visited), frontier=list(stack),
                path_edges=tree_edges, ds=ds(active=0),
            ))
    tree_edges = [[parent[i], i] for i in visited if parent.get(i) is not None]
    if goal is not None:
        steps.append(g.step(
            f"The stack is empty and {g.n(goal)} was never reached → there is no path from {g.n(start)}.",
            "done", status="not_found", visited=list(visited), path_edges=tree_edges, ds=ds(),
        ))
        return {"ok": False, "outcome": "NOT REACHABLE", "steps": steps}
    steps.append(g.step(
        f"The stack is empty → DFS is finished. Visit order: {g.names_of(visited)}.",
        "done", status="found", visited=list(visited), path_edges=tree_edges, ds=ds(),
    ))
    return {"ok": True, "outcome": f"VISITED {len(visited)} NODES", "steps": steps}


# ============================================================== Dijkstra
def _no_negative(g: Graph, algo: str) -> None:
    neg = [(u, v, w) for u, v, w in g.edges if w < 0]
    if neg:
        u, v, w = neg[0]
        raise GraphError(
            f"{algo} needs non-negative edge weights, but {g.e(u, v)} has weight {_num(w)}. Use Bellman-Ford instead."
        )


def dijkstra(g: Graph, start: int, goal: Optional[int]) -> dict:
    _no_negative(g, "Dijkstra")
    steps: list[dict] = []
    dist = {i: INF for i in g.ids}
    dist[start] = 0
    prev: dict[int, Optional[int]] = {start: None}
    heap: list[tuple[float, int]] = [(0, start)]
    done: list[int] = []

    def stale() -> set:
        return {(n, d) for d, n in heap if n in done or d > dist[n]}

    def ds(active=False):
        return _pq(g, heap, stale(), "Priority queue (smallest distance first)", active_top=active)

    def tree_edges():
        return [[prev[i], i] for i in done if prev.get(i) is not None]

    steps.append(g.step(
        f"Set every distance to ∞ except {g.n(start)} = 0, and put ({g.n(start)}, 0) in the priority queue.",
        "init", current=start, labels=_dist_labels(g, dist), frontier=[start], ds=ds(),
    ))
    while heap:
        d, node = heap[0]
        steps.append(g.step(
            f"Take the entry with the smallest distance: {g.n(node)} ({_num(d)}).", "pop",
            current=node, visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(active=True),
        ))
        heapq.heappop(heap)
        if node in done:
            steps.append(g.step(
                f"{g.n(node)} is already final — this is an old, outdated entry → skip it.", "skip",
                current=node, visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
            ))
            continue
        done.append(node)
        steps.append(g.step(
            f"{g.n(node)} is now final: its shortest distance is {_num(d)}.", "final",
            current=node, visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
        ))
        if node == goal:
            p = g.path(prev, goal)
            steps.append(g.step(
                f"{g.n(goal)} is final → shortest path {g.path_text(p)} with total weight {_num(dist[goal])}.",
                "found", status="found", current=node, visited=list(done), labels=_dist_labels(g, dist),
                path_nodes=p, path_edges=g.pairs(p), ds=ds(),
            ))
            return {"ok": True, "outcome": f"DISTANCE {_num(dist[goal])}", "steps": steps, "path": p}
        for nb, w in g.adj[node]:
            if nb in done:
                steps.append(g.step(
                    f"Edge {g.e(node, nb)}: {g.n(nb)} is already final → nothing to improve.", "norelax",
                    current=node, active_edge=[node, nb], visited=list(done), labels=_dist_labels(g, dist),
                    path_edges=tree_edges(), ds=ds(),
                ))
                continue
            new = d + w
            if new < dist[nb]:
                old = dist[nb]
                dist[nb] = new
                prev[nb] = node
                heapq.heappush(heap, (new, nb))
                steps.append(g.step(
                    f"Edge {g.e(node, nb)} (weight {_num(w)}): {_num(d)} + {_num(w)} = {_num(new)} < {_num(old)} → "
                    f"relax: distance of {g.n(nb)} becomes {_num(new)}, push ({g.n(nb)}, {_num(new)}).",
                    "relax", current=node, active_edge=[node, nb], visited=list(done), labels=_dist_labels(g, dist),
                    path_edges=tree_edges(), ds=ds(),
                ))
            else:
                steps.append(g.step(
                    f"Edge {g.e(node, nb)} (weight {_num(w)}): {_num(d)} + {_num(w)} = {_num(new)} ≥ {_num(dist[nb])} → "
                    f"no improvement.",
                    "norelax", current=node, active_edge=[node, nb], visited=list(done), labels=_dist_labels(g, dist),
                    path_edges=tree_edges(), ds=ds(),
                ))
    if goal is not None:
        steps.append(g.step(
            f"The priority queue is empty and {g.n(goal)} is still ∞ → not reachable from {g.n(start)}.",
            "done", status="not_found", visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
        ))
        return {"ok": False, "outcome": "NOT REACHABLE", "steps": steps}
    reach = [f"{g.n(i)}={_num(dist[i])}" for i in g.ids]
    steps.append(g.step(
        "The priority queue is empty → all shortest distances are final: " + ", ".join(reach) + ".",
        "done", status="found", visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
    ))
    return {"ok": True, "outcome": "ALL DISTANCES", "steps": steps}


# ========================================================= greedy search
def greedy(g: Graph, start: int, goal: int) -> dict:
    steps: list[dict] = []
    parent: dict[int, Optional[int]] = {start: None}
    heap: list[tuple[float, int]] = [(g.h(start, goal), start)]
    visited: list[int] = []
    hl = {i: f"h={_num(g.h(i, goal))}" for i in g.ids}

    def ds(active=False):
        return _pq(g, heap, set(), "Priority queue (smallest h first)", active_top=active)

    def tree_edges():
        return [[parent[i], i] for i in parent if parent[i] is not None and i in visited]

    steps.append(g.step(
        f"Greedy best-first search only looks at h = straight-line distance to {g.n(goal)} "
        f"(screen distance / {H_SCALE}). Put {g.n(start)} in the priority queue.",
        "init", current=start, labels=hl, frontier=[start], ds=ds(),
    ))
    while heap:
        hv, node = heap[0]
        steps.append(g.step(
            f"Take the node that looks closest to the goal: {g.n(node)} (h={_num(hv)}).", "pop",
            current=node, visited=list(visited), labels=hl, path_edges=tree_edges(), ds=ds(active=True),
        ))
        heapq.heappop(heap)
        if node in visited:
            steps.append(g.step(f"{g.n(node)} was already expanded → skip.", "skip",
                                current=node, visited=list(visited), labels=hl, ds=ds()))
            continue
        visited.append(node)
        if node == goal:
            p = g.path(parent, goal)
            c = g.cost(p)
            steps.append(g.step(
                f"{g.n(goal)} reached! Path {g.path_text(p)} with total weight {_num(c)}. Greedy search is fast, "
                f"but this is not guaranteed to be the shortest path.",
                "found", status="found", current=node, visited=list(visited), labels=hl,
                path_nodes=p, path_edges=g.pairs(p), ds=ds(),
            ))
            return {"ok": True, "outcome": f"FOUND · COST {_num(c)}", "steps": steps, "path": p}
        for nb, _ in g.adj[node]:
            if nb in visited or nb in parent:
                steps.append(g.step(
                    f"Edge {g.e(node, nb)}: {g.n(nb)} is already known → skip.", "skip",
                    current=node, active_edge=[node, nb], visited=list(visited), labels=hl, path_edges=tree_edges(), ds=ds(),
                ))
                continue
            parent[nb] = node
            heapq.heappush(heap, (g.h(nb, goal), nb))
            steps.append(g.step(
                f"Edge {g.e(node, nb)}: add {g.n(nb)} with h={_num(g.h(nb, goal))}.", "push",
                current=node, active_edge=[node, nb], visited=list(visited), labels=hl, path_edges=tree_edges(), ds=ds(),
            ))
    steps.append(g.step(
        f"The priority queue is empty → {g.n(goal)} cannot be reached from {g.n(start)}.",
        "done", status="not_found", visited=list(visited), labels=hl, ds=ds(),
    ))
    return {"ok": False, "outcome": "NOT REACHABLE", "steps": steps}


# =================================================================== A*
def a_star(g: Graph, start: int, goal: int) -> dict:
    _no_negative(g, "A*")
    steps: list[dict] = []
    gs: dict[int, float] = {start: 0}
    prev: dict[int, Optional[int]] = {start: None}
    heap: list[tuple[float, float, int]] = [(g.h(start, goal), 0, start)]
    closed: list[int] = []

    def labels():
        return {i: (f"g={_num(gs[i])} h={_num(g.h(i, goal))}" if i in gs else f"h={_num(g.h(i, goal))}") for i in g.ids}

    def stale():
        return {(n, f) for f, gv, n in heap if n in closed or gv > gs.get(n, INF)}

    def ds(active=False):
        return _pq(g, [(f, n) for f, _, n in heap], stale(), "Priority queue (smallest f = g + h first)", active_top=active)

    def tree_edges():
        return [[prev[i], i] for i in closed if prev.get(i) is not None]

    steps.append(g.step(
        f"A* orders nodes by f = g + h: g = distance travelled so far, h = straight-line estimate to {g.n(goal)} "
        f"(screen distance / {H_SCALE}). Start: g({g.n(start)}) = 0.",
        "init", current=start, labels=labels(), frontier=[start], ds=ds(),
    ))
    while heap:
        f, gv, node = heap[0]
        steps.append(g.step(
            f"Take the node with the smallest f: {g.n(node)} (f = {_num(gv)} + {_num(g.h(node, goal))} = {_num(f)}).",
            "pop", current=node, visited=list(closed), labels=labels(), path_edges=tree_edges(), ds=ds(active=True),
        ))
        heapq.heappop(heap)
        if node in closed:
            steps.append(g.step(f"{g.n(node)} is already closed — outdated entry → skip.", "skip",
                                current=node, visited=list(closed), labels=labels(), path_edges=tree_edges(), ds=ds()))
            continue
        if node == goal:
            closed.append(node)
            p = g.path(prev, goal)
            steps.append(g.step(
                f"{g.n(goal)} reached! Shortest path {g.path_text(p)} with total weight {_num(gs[goal])}.",
                "found", status="found", current=node, visited=list(closed), labels=labels(),
                path_nodes=p, path_edges=g.pairs(p), ds=ds(),
            ))
            return {"ok": True, "outcome": f"DISTANCE {_num(gs[goal])}", "steps": steps, "path": p}
        closed.append(node)
        steps.append(g.step(f"Close {g.n(node)} and look at its neighbours.", "close",
                            current=node, visited=list(closed), labels=labels(), path_edges=tree_edges(), ds=ds()))
        for nb, w in g.adj[node]:
            if nb in closed:
                steps.append(g.step(
                    f"Edge {g.e(node, nb)}: {g.n(nb)} is closed → skip.", "norelax",
                    current=node, active_edge=[node, nb], visited=list(closed), labels=labels(), path_edges=tree_edges(), ds=ds(),
                ))
                continue
            new_g = gs[node] + w
            if new_g < gs.get(nb, INF):
                gs[nb] = new_g
                prev[nb] = node
                fv = new_g + g.h(nb, goal)
                heapq.heappush(heap, (fv, new_g, nb))
                steps.append(g.step(
                    f"Edge {g.e(node, nb)} (weight {_num(w)}): g({g.n(nb)}) = {_num(gs[node])} + {_num(w)} = {_num(new_g)}, "
                    f"f = {_num(new_g)} + {_num(g.h(nb, goal))} = {_num(fv)} → push.",
                    "relax", current=node, active_edge=[node, nb], visited=list(closed), labels=labels(),
                    path_edges=tree_edges(), ds=ds(),
                ))
            else:
                steps.append(g.step(
                    f"Edge {g.e(node, nb)}: {_num(new_g)} is not better than g({g.n(nb)}) = {_num(gs[nb])} → skip.",
                    "norelax", current=node, active_edge=[node, nb], visited=list(closed), labels=labels(),
                    path_edges=tree_edges(), ds=ds(),
                ))
    steps.append(g.step(
        f"The priority queue is empty → {g.n(goal)} cannot be reached from {g.n(start)}.",
        "done", status="not_found", visited=list(closed), labels=labels(), ds=ds(),
    ))
    return {"ok": False, "outcome": "NOT REACHABLE", "steps": steps}


# ========================================================= Bellman-Ford
MAX_BF_STEPS = 500


def bellman_ford(g: Graph, start: int) -> dict:
    steps: list[dict] = []
    edges = g.directed_edges()
    dist = {i: INF for i in g.ids}
    dist[start] = 0
    prev: dict[int, Optional[int]] = {start: None}

    def tree_edges():
        return [[prev[i], i] for i in g.ids if prev.get(i) is not None]

    def ds(active=None):
        return _table(g, dist, prev, "Distance table", active)

    extra = "" if g.directed else " (each undirected edge is used in both directions)"
    steps.append(g.step(
        f"Set every distance to ∞ except {g.n(start)} = 0. Then relax all {len(edges)} edges{extra}, "
        f"up to {len(g.ids) - 1} rounds (number of nodes − 1).",
        "init", current=start, labels=_dist_labels(g, dist), ds=ds(start),
    ))
    rounds = max(len(g.ids) - 1, 0)
    for r in range(1, rounds + 1):
        changed = 0
        steps.append(g.step(f"Round {r}: go through every edge once.", "round",
                            labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds()))
        for u, v, w in edges:
            if dist[u] == INF or dist[u] + w >= dist[v]:
                continue  # nothing to do (not shown, to keep the steps short)
            old = dist[v]
            dist[v] = dist[u] + w
            prev[v] = u
            changed += 1
            if len(steps) < MAX_BF_STEPS:
                steps.append(g.step(
                    f"Round {r}, edge {g.e(u, v)} (weight {_num(w)}): {_num(dist[u])} + {_num(w)} = {_num(dist[v])} "
                    f"< {_num(old)} → relax: distance of {g.n(v)} = {_num(dist[v])}.",
                    "relax", current=v, active_edge=[u, v], labels=_dist_labels(g, dist),
                    path_edges=tree_edges(), ds=ds(v),
                ))
        if changed == 0:
            steps.append(g.step(
                f"Round {r}: no distance changed → the distances are final, stop early.", "early",
                labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
            ))
            break
        steps.append(g.step(f"Round {r} finished: {changed} distance(s) improved.", "round",
                            labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds()))

    steps.append(g.step(
        "Check for negative cycles: if any edge can still be relaxed, a negative cycle exists.", "check",
        labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
    ))
    for u, v, w in edges:
        if dist[u] != INF and dist[u] + w < dist[v]:
            # walk back n times to land inside the cycle, then collect it
            prev[v] = u
            x = v
            for _ in range(len(g.ids)):
                x = prev.get(x) if prev.get(x) is not None else x
            cycle = [x]
            y = prev.get(x)
            while y is not None and y != x and len(cycle) <= len(g.ids):
                cycle.append(y)
                y = prev.get(y)
            cycle.append(x)
            cycle.reverse()
            total = sum(min(ww for vv, ww in g.adj[a] if vv == b) for a, b in zip(cycle, cycle[1:]))
            steps.append(g.step(
                f"Edge {g.e(u, v)} can still be relaxed → NEGATIVE CYCLE {g.path_text(cycle)} "
                f"(total weight {_num(total)}). Going around it again and again makes the distance smaller forever, "
                f"so shortest paths are not defined.",
                "negcycle", status="not_found", active_edge=[u, v], cycle_nodes=cycle[:-1],
                cycle_edges=g.pairs(cycle), labels=_dist_labels(g, dist), ds=ds(),
            ))
            return {"ok": False, "outcome": "NEGATIVE CYCLE", "steps": steps, "cycle": cycle}

    reach = [f"{g.n(i)}={_num(dist[i])}" for i in g.ids]
    steps.append(g.step(
        "No edge can be relaxed any more → no negative cycle. Shortest distances: " + ", ".join(reach) + ".",
        "done", status="found", labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
    ))
    return {"ok": True, "outcome": "ALL DISTANCES", "steps": steps}


# ===================================================== topological sort
def topo_sort(g: Graph) -> dict:
    if not g.directed:
        raise GraphError("Topological sort only works on a directed graph (with no cycles).")
    steps: list[dict] = []
    indeg = {i: 0 for i in g.ids}
    for u, v, _ in g.edges:
        indeg[v] += 1
    queue = [i for i in g.ids if indeg[i] == 0]
    order: list[int] = []

    def labels():
        return {i: f"in={indeg[i]}" for i in g.ids if i not in order}

    steps.append(g.step(
        "Count the incoming edges (in-degree) of every node. Nodes with in-degree 0 have nothing before them, "
        f"so they can go first: {g.names_of(queue) or 'none'}.",
        "zero", labels=labels(), frontier=list(queue), ds=_queue(g, queue),
    ))
    while queue:
        u = queue[0]
        steps.append(g.step(
            f"Take {g.n(u)} from the queue and append it to the order.", "pop",
            current=u, visited=list(order), labels=labels(), frontier=list(queue), ds=_queue(g, queue, active=0),
        ))
        queue.pop(0)
        order.append(u)
        for v, _ in g.adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
                steps.append(g.step(
                    f"Remove edge {g.e(u, v)}: in-degree of {g.n(v)} drops to 0 → add it to the queue.", "push",
                    current=u, active_edge=[u, v], visited=list(order), labels=labels(), frontier=list(queue),
                    ds=_queue(g, queue, active=len(queue) - 1),
                ))
            else:
                steps.append(g.step(
                    f"Remove edge {g.e(u, v)}: in-degree of {g.n(v)} drops to {indeg[v]}.", "edge",
                    current=u, active_edge=[u, v], visited=list(order), labels=labels(), frontier=list(queue),
                    ds=_queue(g, queue),
                ))
    if len(order) < len(g.ids):
        rest = [i for i in g.ids if i not in order]
        steps.append(g.step(
            f"The queue is empty but {g.names_of(rest)} still have incoming edges → they lie on a CYCLE. "
            "A graph with a cycle has no topological order.",
            "cycle", status="not_found", visited=list(order), cycle_nodes=rest, labels=labels(), ds=_queue(g, []),
        ))
        return {"ok": False, "outcome": "HAS A CYCLE", "steps": steps}
    steps.append(g.step(
        f"Every node is placed → topological order: {g.names_of(order)}. Every edge goes from left to right.",
        "done", status="found", visited=list(order), path_nodes=order, ds=_queue(g, []),
    ))
    return {"ok": True, "outcome": "ORDER FOUND", "steps": steps, "order": order}


# ========================================================== cycle check
def cycle_check(g: Graph, with_steps: bool = True) -> dict:
    """DFS cycle detection (directed: back edge to a GRAY node; undirected: visited non-parent)."""
    steps: list[dict] = []
    rec = with_steps
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in g.ids}
    frames: list[str] = []
    stack_nodes: list[int] = []
    found: list[list[int]] = []

    def ds():
        return _stack(g, list(reversed(frames)), "Call stack of dfs() (top first)")

    def hl(**kw):
        gray = [i for i in g.ids if color[i] == GRAY]
        black = [i for i in g.ids if color[i] == BLACK]
        return {"frontier": gray, "visited": black + gray, **kw}

    def finish_cycle(u: int, v: int) -> list[int]:
        i = stack_nodes.index(v)
        return stack_nodes[i:] + [v]

    def visit(u: int, parent: Optional[int]) -> bool:
        color[u] = GRAY
        stack_nodes.append(u)
        frames.append(f"dfs({g.n(u)})" if g.directed else f"dfs({g.n(u)}, parent={g.n(parent) if parent is not None else '–'})")
        if rec:
            steps.append(g.step(
                f"Visit {g.n(u)}" + (" — it is now GRAY (on the current path)." if g.directed else "."),
                "visit", ds=ds(), **hl(current=u),
            ))
        for v, _ in g.adj[u]:
            if not g.directed and v == parent:
                if rec:
                    steps.append(g.step(
                        f"Edge {g.e(u, v)}: {g.n(v)} is the parent — that's the edge we came by → skip.",
                        "skip", ds=ds(), **hl(current=u, active_edge=[u, v]),
                    ))
                continue
            if (g.directed and color[v] == GRAY) or (not g.directed and color[v] != WHITE):
                cyc = finish_cycle(u, v)
                found.append(cyc)
                if rec:
                    why = (f"{g.n(v)} is GRAY (still on the current path) → back edge"
                           if g.directed else f"{g.n(v)} was already visited and is not the parent")
                    steps.append(g.step(
                        f"Edge {g.e(u, v)}: {why} → CYCLE {g.path_text(cyc)}.",
                        "cycle", status="not_found", ds=ds(),
                        **hl(current=u, active_edge=[u, v], cycle_nodes=cyc[:-1], cycle_edges=g.pairs(cyc)),
                    ))
                return True
            if color[v] == WHITE:
                if rec:
                    steps.append(g.step(
                        f"Edge {g.e(u, v)}: {g.n(v)} not visited yet → go deeper.",
                        "descend", ds=ds(), **hl(current=u, active_edge=[u, v]),
                    ))
                if visit(v, u):
                    return True
            elif rec:  # directed and BLACK
                steps.append(g.step(
                    f"Edge {g.e(u, v)}: {g.n(v)} is BLACK (fully explored earlier) → no cycle through it.",
                    "skip", ds=ds(), **hl(current=u, active_edge=[u, v]),
                ))
        color[u] = BLACK
        stack_nodes.pop()
        frames.pop()
        if rec:
            steps.append(g.step(
                f"All edges of {g.n(u)} checked → {g.n(u)} is finished" + (" (BLACK)." if g.directed else "."),
                "finish", ds=ds(), **hl(current=u),
            ))
        return False

    if rec:
        intro = ("Directed graph: DFS colors nodes WHITE (new), GRAY (on the current path), BLACK (finished). "
                 "An edge to a GRAY node closes a cycle.") if g.directed else (
                 "Undirected graph: DFS remembers each node's parent. Reaching an already visited node that is "
                 "not the parent closes a cycle.")
        steps.append(g.step(intro, "init", ds=ds()))

    components = 0
    for s in g.ids:
        if color[s] != WHITE:
            continue
        components += 1
        if rec:
            steps.append(g.step(f"Start a new DFS from {g.n(s)}.", "start", ds=ds(), **hl(current=s)))
        if visit(s, None):
            cyc = found[0]
            return {
                "ok": False, "outcome": "CYCLIC", "steps": steps,
                "cyclic": True, "cycle": cyc, "cycle_text": g.path_text(cyc),
            }

    if rec:
        msg = ("No back edge found → the graph is ACYCLIC (a DAG)." if g.directed else
               f"No cycle found → the graph is ACYCLIC (a forest of {components} tree(s)).")
        steps.append(g.step(msg, "done", status="found", ds=ds(), **hl()))
    return {"ok": True, "outcome": "ACYCLIC", "steps": steps, "cyclic": False, "cycle": [], "components": components}


ALGORITHMS = {
    "cycle": ("Cycle check", False, False),  # (title, needs start, needs goal)
    "bfs": ("BFS", True, False),
    "dfs": ("DFS", True, False),
    "dijkstra": ("Dijkstra", True, False),
    "greedy": ("Greedy best-first search", True, True),
    "astar": ("A*", True, True),
    "bellman_ford": ("Bellman-Ford", True, False),
    "topo": ("Topological sort", False, False),
}


def run(g: Graph, algorithm: str, start: Any = None, goal: Any = None) -> dict:
    if algorithm not in ALGORITHMS:
        raise GraphError(f"Unknown algorithm '{algorithm}'.")
    if not g.ids:
        raise GraphError("The graph is empty — create some nodes first.")
    title, need_start, need_goal = ALGORITHMS[algorithm]
    s = g.node_id(start, "start") if need_start else None
    t = None
    if need_goal or (goal is not None and algorithm in ("bfs", "dfs", "dijkstra")):
        t = g.node_id(goal, "goal")
    if algorithm == "cycle":
        return cycle_check(g)
    if algorithm == "topo":
        return topo_sort(g)
    if algorithm == "bfs":
        return bfs(g, s, t)
    if algorithm == "dfs":
        return dfs(g, s, t)
    if algorithm == "dijkstra":
        return dijkstra(g, s, t)
    if algorithm == "greedy":
        return greedy(g, s, t)
    if algorithm == "astar":
        return a_star(g, s, t)
    return bellman_ford(g, s)
