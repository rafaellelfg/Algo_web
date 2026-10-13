"""Python code shown next to the graph visualization.

`#@tag` at the end of a line = the line that runs in a step with that tag
(the frontend hides the markers and highlights the line).
`graph[u]` is the list of (neighbour, weight) pairs of u.
"""

BFS = '''\
from collections import deque

def bfs(graph, start, goal=None):
    visited = {start}                              #@init
    parent = {start: None}
    queue = deque([start])           # FIFO queue
    while queue:
        node = queue.popleft()                     #@pop
        if node == goal:
            return path(parent, goal)    # fewest edges   #@found
        for nb, _ in graph[node]:
            if nb in visited:
                continue                 # seen already   #@skip
            visited.add(nb)                        #@push
            parent[nb] = node
            queue.append(nb)
    return visited                   # or None: goal unreachable   #@done
'''

DFS = '''\
def dfs(graph, start, goal=None):
    stack = [start]                  # LIFO stack  #@init
    parent = {start: None}
    visited = []
    while stack:
        node = stack.pop()                         #@pop
        if node in visited:
            continue                     # old entry   #@skip
        visited.append(node)                       #@visit
        if node == goal:
            return path(parent, goal)              #@found
        for nb, _ in reversed(graph[node]):
            if nb not in visited:
                parent[nb] = node                  #@push
                stack.append(nb)
    return visited                   # or None: goal unreachable   #@done
'''

DIJKSTRA = '''\
import heapq

def dijkstra(graph, start, goal=None):
    # needs: NO negative edge weights (cycles are fine)
    dist = {v: float("inf") for v in graph}        #@init
    dist[start] = 0
    prev = {start: None}
    pq = [(0, start)]                # min-heap of (distance, node)
    done = set()
    while pq:
        d, node = heapq.heappop(pq)                #@pop
        if node in done:
            continue                     # outdated entry   #@skip
        done.add(node)                   # distance is final   #@final
        if node == goal:
            return path(prev, goal), d             #@found
        for nb, w in graph[node]:
            if nb not in done and d + w < dist[nb]:    #@relax
                dist[nb] = d + w
                prev[nb] = node
                heapq.heappush(pq, (dist[nb], nb))
            # else: no improvement                 #@norelax
    return dist, prev                              #@done
'''

GREEDY = '''\
import heapq

def greedy_best_first(graph, start, goal, h):
    # h(v) = straight-line distance from v to the goal
    pq = [(h(start), start)]         # ordered by h ONLY   #@init
    parent = {start: None}
    visited = set()
    while pq:
        _, node = heapq.heappop(pq)                #@pop
        if node in visited:
            continue                               #@skip
        visited.add(node)
        if node == goal:
            return path(parent, goal)    # not always shortest!   #@found
        for nb, _ in graph[node]:
            if nb not in parent:
                parent[nb] = node                  #@push
                heapq.heappush(pq, (h(nb), nb))
    return None                      # goal unreachable   #@done
'''

ASTAR = '''\
import heapq

def a_star(graph, start, goal, h):
    # needs: NO negative weights, h never overestimates
    g = {start: 0}                   # cost so far #@init
    prev = {start: None}
    pq = [(h(start), start)]         # ordered by f = g + h
    closed = set()
    while pq:
        f, node = heapq.heappop(pq)                #@pop
        if node in closed:
            continue                     # outdated entry   #@skip
        if node == goal:
            return path(prev, goal), g[goal]       #@found
        closed.add(node)                           #@close
        for nb, w in graph[node]:
            if nb in closed:
                continue                           #@norelax
            new_g = g[node] + w
            if new_g < g.get(nb, float("inf")):    #@relax
                g[nb] = new_g
                prev[nb] = node
                heapq.heappush(pq, (new_g + h(nb), nb))
    return None                      # goal unreachable   #@done
'''

BELLMAN_FORD = '''\
def bellman_ford(nodes, edges, start):
    # negative weights are OK, but NO negative cycles
    dist = {v: float("inf") for v in nodes}        #@init
    dist[start] = 0
    prev = {start: None}
    for i in range(len(nodes) - 1):                #@round
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:              #@relax
                dist[v] = dist[u] + w
                prev[v] = u
                changed = True
        if not changed:
            break                        # early stop  #@early
    for u, v, w in edges:                          #@check
        if dist[u] + w < dist[v]:
            raise ValueError("negative cycle")     #@negcycle
    return dist, prev                              #@done
'''

TOPO = '''\
from collections import deque

def topological_sort(graph):
    # directed graph with NO cycles (a DAG)
    indeg = {v: 0 for v in graph}
    for u in graph:
        for v, _ in graph[u]:
            indeg[v] += 1
    queue = deque(v for v in graph if indeg[v] == 0)   #@zero
    order = []
    while queue:
        u = queue.popleft()                        #@pop
        order.append(u)
        for v, _ in graph[u]:
            indeg[v] -= 1                          #@edge
            if indeg[v] == 0:
                queue.append(v)                    #@push
    if len(order) < len(graph):
        raise ValueError("graph has a cycle")      #@cycle
    return order                                   #@done
'''

CYCLE_DIRECTED = '''\
WHITE, GRAY, BLACK = 0, 1, 2

def has_cycle(graph):                # directed graph
    color = {v: WHITE for v in graph}              #@init

    def dfs(u):
        color[u] = GRAY              # on the current path   #@visit
        for v, _ in graph[u]:
            if color[v] == GRAY:
                return True          # back edge -> CYCLE    #@cycle
            if color[v] == WHITE:
                if dfs(v):                         #@descend
                    return True
            # BLACK: finished earlier, no cycle    #@skip
        color[u] = BLACK             # finished    #@finish
        return False

    for v in graph:
        if color[v] == WHITE and dfs(v):           #@start
            return True
    return False                     # acyclic (DAG)   #@done
'''

CYCLE_UNDIRECTED = '''\
def has_cycle(graph):                # undirected graph
    visited = set()                                #@init

    def dfs(u, parent):
        visited.add(u)                             #@visit
        for v, _ in graph[u]:
            if v == parent:
                continue             # the edge we came by   #@skip
            if v in visited:
                return True          # CYCLE       #@cycle
            if dfs(v, u):                          #@descend
                return True
        return False                 # u finished  #@finish

    for v in graph:
        if v not in visited and dfs(v, None):      #@start
            return True
    return False                     # acyclic (forest)   #@done
'''

CODE = {
    "bfs": BFS,
    "dfs": DFS,
    "dijkstra": DIJKSTRA,
    "greedy": GREEDY,
    "astar": ASTAR,
    "bellman_ford": BELLMAN_FORD,
    "topo": TOPO,
}


def code_for(algorithm: str, directed: bool) -> str:
    if algorithm == "cycle":
        return CYCLE_DIRECTED if directed else CYCLE_UNDIRECTED
    return CODE.get(algorithm, "")
