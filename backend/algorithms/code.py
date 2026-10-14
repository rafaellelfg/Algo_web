"""The Python code shown next to the visualizations (trees and graphs).

Each snippet is plain, readable Python. A comment `#@tag1,tag2` at the end of
a line marks it: every algorithm step carries a `code` tag, and the frontend
highlights the line(s) with that tag (the markers themselves are not shown).
"""

BST_SEARCH = '''\
def search(root, target):
    node = root                                    #@start
    while node is not None:
        if target == node.value:                   #@equal
            return node              # FOUND
        elif target < node.value:
            node = node.left                       #@left
        else:
            node = node.right                      #@right
    return None                      # NOT FOUND   #@notfound
'''

BST_INSERT = '''\
def insert(root, value):
    if root is None:
        return Node(value)           # new root    #@empty
    node = root                                    #@start
    while True:
        if value == node.value:
            return root              # duplicate   #@equal
        if value < node.value:
            if node.left is None:
                node.left = Node(value)            #@attach_left,done
                return root
            node = node.left                       #@left
        else:
            if node.right is None:
                node.right = Node(value)           #@attach_right,done
                return root
            node = node.right                      #@right
'''

BST_DELETE = '''\
def delete(root, target):
    parent, node = None, root                      #@start
    while node is not None and node.value != target:
        parent = node
        if target < node.value:
            node = node.left                       #@left
        else:
            node = node.right                      #@right
    if node is None:
        return root                  # NOT FOUND   #@notfound
    # node.value == target                         #@equal

    if node.left is None and node.right is None:   #@case1
        replace_child(parent, node, None)    # leaf: remove
    elif node.left is None or node.right is None:  #@case2
        child = node.left or node.right
        replace_child(parent, node, child)   # child moves up
    else:                                          #@case3
        succ = node.right                          #@succ_right
        while succ.left is not None:
            succ = succ.left                       #@succ_left
        # succ = smallest value of the right subtree   #@succ
        node.value = succ.value      # copy it up  #@copy
        replace_child(succ.parent, succ, succ.right)   #@remove_succ
    return root                                    #@done
'''

RB_INSERT = '''\
def rb_insert(tree, value):
    z = bst_insert(tree, value)      # plain BST insert   #@start,left,right,equal,empty,attach_left,attach_right
    z.color = RED                                  #@red
    while z.parent is not None and z.parent.color == RED:
        p = z.parent
        g = p.parent                     # grandparent
        u = g.right if p is g.left else g.left   # uncle
        if u is not None and u.color == RED:       #@case1
            # Case 1: recolor and move up
            p.color = u.color = BLACK
            g.color = RED
            z = g
        else:
            if is_inner_child(z):                  #@case2
                # Case 2: rotate at p -> becomes Case 3
                rotate(p, direction=side_of(p))
                z, p = p, z
            # Case 3: recolor, rotate at grandparent   #@case3
            p.color, g.color = BLACK, RED
            rotate(g, direction=opposite(side_of(p)))
    tree.root.color = BLACK              # rule 2  #@root
    return z                                       #@done
'''

RB_DELETE = '''\
def rb_delete(tree, target):
    z = bst_search(tree.root, target)              #@start,left,right,equal,notfound
    if z is None:
        return                           # NOT FOUND
    if z.left and z.right:                         #@two
        y = z.right                                #@succ_right
        while y.left:
            y = y.left                             #@succ_left
        # y = in-order successor                   #@succ
        z.value = y.value                          #@copy
    else:
        y = z
    x = y.left or y.right                # at most one child
    replace_child(y.parent, y, x)                  #@remove
    if y.color == RED:                             #@red
        return                           # no black depth changed
    if x is not None and x.color == RED:           #@redchild
        x.color = BLACK
        return
    fix_double_black(tree, x, y.parent)            #@db

def fix_double_black(tree, x, parent):
    while x is not tree.root and is_black(x):
        w = sibling(x, parent)
        if w.color == RED:                         #@d1
            w.color, parent.color = BLACK, RED     # Case 1
            rotate(parent, towards=x)
        elif is_black(w.left) and is_black(w.right):   #@d2
            w.color = RED                          # Case 2
            x, parent = parent, parent.parent
        elif is_black(far_child(w, x)):            #@d3
            near_child(w, x).color = BLACK         # Case 3
            w.color = RED
            rotate(w, away_from=x)
        else:                                      #@d4
            w.color = parent.color                 # Case 4
            parent.color = BLACK
            far_child(w, x).color = BLACK
            rotate(parent, towards=x)
            x = tree.root
    if x is not None:
        x.color = BLACK                            #@dfinal
    # done                                         #@done
'''

RB_BLACK_DEPTH = '''\
def black_depth(root):
    if root.color != BLACK:                        #@root
        return "invalid: the root must be black"
    path_depths = set()

    def visit(node, depth):
        if node is None:                           #@nil
            path_depths.add(depth)       # one root-to-NIL path
            return
        if node.color == BLACK:                    #@node
            depth += 1                   # red nodes don't count
        elif node.parent and node.parent.color == RED:
            raise ValueError("red node with a red parent")
        visit(node.left, depth)
        visit(node.right, depth)

    visit(root, 0)
    if len(path_depths) == 1:                      #@result
        return path_depths.pop()         # = black height
    return "invalid: different black depths"
'''

RB_PAINT = '''\
def paint(root):
    # 1) bottom-up: which black heights can each subtree have?   #@start
    def heights(node):
        if node is None:
            return {0}, set()            # NIL: black, height 0
        lb, lr = heights(node.left)
        rb, rr = heights(node.right)
        node.B = {h + 1 for h in (lb | lr) & (rb | rr)}  # node black   #@sets
        node.R = lb & rb                 # node red: kids must be black
        if not node.B and not node.R:
            raise ValueError("cannot be painted")      #@fail
        return node.B, node.R

    heights(root)
    # 2) top-down: the root is black
    def color(node, c, h):
        if node is None:
            return
        node.color = c                             #@color
        for kid in (node.left, node.right):
            if c == BLACK:
                color(kid, BLACK if kid and h - 1 in kid.B else RED, h - 1)
            else:
                color(kid, BLACK, h)

    color(root, BLACK, max(root.B))                #@choose
    return root                      # valid red-black tree   #@done
'''

TREE_CODE = {
    ("bst", "search"): BST_SEARCH,
    ("bst", "insert"): BST_INSERT,
    ("bst", "delete"): BST_DELETE,
    ("bst", "paint"): RB_PAINT,
    ("rb", "search"): BST_SEARCH,
    ("rb", "insert"): RB_INSERT,
    ("rb", "delete"): RB_DELETE,
    ("rb", "black_depth"): RB_BLACK_DEPTH,
}


def tree_code(tree_kind: str, op: str) -> str:
    return TREE_CODE.get((tree_kind, op), "")


# ======================================================================
# Graphs   (graph[u] is the list of (neighbour, weight) pairs of u)
# ======================================================================

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

GRAPH_CODE = {
    "bfs": BFS,
    "dfs": DFS,
    "dijkstra": DIJKSTRA,
    "greedy": GREEDY,
    "astar": ASTAR,
    "bellman_ford": BELLMAN_FORD,
    "topo": TOPO,
}


def graph_code(algorithm: str, directed: bool) -> str:
    if algorithm == "cycle":
        return CYCLE_DIRECTED if directed else CYCLE_UNDIRECTED
    return GRAPH_CODE.get(algorithm, "")
