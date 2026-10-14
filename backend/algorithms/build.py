"""BUILD the data structures.

Everything needed to create and store the structures the algorithms run on:

* Node, BinarySearchTree   build a BST from a list of numbers, load it from JSON
* RedBlackTree             a BST that keeps itself balanced (insert = BST insert
                           + recolor / rotate), loading checks the red-black rules
* Graph                    a directed or undirected weighted graph built from the
                           nodes / edges JSON the frontend sends

The step-by-step algorithms that run on these structures live in algorithms.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

RED, BLACK = "red", "black"


class TreeFormatError(ValueError):
    """Raised when a tree sent by the client is malformed."""


@dataclass(eq=False)
class Node:
    id: int
    value: float
    left: Optional["Node"] = None
    right: Optional["Node"] = None
    color: Optional[str] = None  # only used by red-black trees
    parent: Optional["Node"] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "value": self.value,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
        }
        if self.color:
            d["color"] = self.color
        return d


def fmt(v: float) -> str:
    """Pretty number for step messages: 5 instead of 5.0."""
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


# ======================================================================
# Binary search tree
# ======================================================================
class BinarySearchTree:
    MAX_NODES = 500
    kind = "bst"

    def __init__(self) -> None:
        self.root: Optional[Node] = None
        self.size = 0
        self._next_id = 0

    # ------------------------------------------------------------------ build
    def insert(self, value: float) -> Optional[Node]:
        """Insert a value (no steps). Returns the new node, or None for a duplicate."""
        parent, side = self._find_slot(value)
        if side == "dup":
            return None
        return self._attach(value, parent, side)

    def _find_slot(self, value: float) -> tuple[Optional[Node], str]:
        """Where would `value` go? -> (parent, "left"/"right"/"root"), or (node, "dup")."""
        current, parent, side = self.root, None, "root"
        while current is not None:
            if value == current.value:
                return current, "dup"
            parent = current
            side = "left" if value < current.value else "right"
            current = current.left if side == "left" else current.right
        return parent, side

    def _attach(self, value: float, parent: Optional[Node], side: str) -> Node:
        node = Node(self._next_id, value, parent=parent)
        self._next_id += 1
        self.size += 1
        if parent is None:
            self.root = node
        elif side == "left":
            parent.left = node
        else:
            parent.right = node
        return node

    @classmethod
    def build(cls, values: list[float]) -> tuple["BinarySearchTree", list[float]]:
        """Build a tree from a list. Returns the tree and the skipped duplicates."""
        tree = cls()
        duplicates: list[float] = []
        for v in values:
            if tree.insert(v) is None:
                duplicates.append(v)
        return tree, duplicates

    @classmethod
    def from_dict(cls, data: Any) -> "BinarySearchTree":
        """Rebuild a tree from the JSON the frontend sends back."""
        tree = cls()
        seen_ids: set[int] = set()

        def parse(d: Any, low: float, high: float, parent: Optional[Node]) -> Optional[Node]:
            if d is None:
                return None
            if not isinstance(d, dict):
                raise TreeFormatError("Each node must be an object.")
            node_id, value = d.get("id"), d.get("value")
            if isinstance(node_id, bool) or not isinstance(node_id, int) or node_id in seen_ids:
                raise TreeFormatError("Every node needs a unique integer 'id'.")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TreeFormatError("Every node needs a numeric 'value'.")
            if not (low < value < high):
                raise TreeFormatError("The tree does not satisfy the BST property.")
            color = d.get("color")
            if color not in (None, RED, BLACK):
                raise TreeFormatError("A node's color must be 'red' or 'black'.")
            seen_ids.add(node_id)
            tree.size += 1
            if tree.size > cls.MAX_NODES:
                raise TreeFormatError(f"The tree is too large (max {cls.MAX_NODES} nodes).")
            node = Node(node_id, value, color=color, parent=parent)
            node.left = parse(d.get("left"), low, value, node)
            node.right = parse(d.get("right"), value, high, node)
            return node

        tree.root = parse(data, float("-inf"), float("inf"), None)
        tree._next_id = max(seen_ids, default=-1) + 1
        tree._after_load()
        return tree

    def _after_load(self) -> None:
        """Hook for subclasses to validate a loaded tree."""
        for node in self._nodes():
            node.color = None  # a plain BST has no colors

    def _nodes(self) -> list[Node]:
        out: list[Node] = []
        stack = [self.root] if self.root else []
        while stack:
            n = stack.pop()
            out.append(n)
            stack.extend(c for c in (n.right, n.left) if c)
        return out

    # ------------------------------------------------------------ properties
    def height(self) -> int:
        def _h(node: Optional[Node]) -> int:
            return 0 if node is None else 1 + max(_h(node.left), _h(node.right))

        return _h(self.root)

    def _traverse(self, order: str) -> list[float]:
        result: list[float] = []

        def walk(node: Optional[Node]) -> None:
            if not node:
                return
            if order == "pre":
                result.append(node.value)
            walk(node.left)
            if order == "in":
                result.append(node.value)
            walk(node.right)
            if order == "post":
                result.append(node.value)

        walk(self.root)
        return result

    def summary(self) -> dict:
        return {
            "kind": self.kind,
            "root": self.snapshot(),
            "size": self.size,
            "height": self.height(),
            "traversals": {
                "inorder": self._traverse("in"),
                "preorder": self._traverse("pre"),
                "postorder": self._traverse("post"),
            },
        }

    def snapshot(self) -> Optional[dict]:
        return self.root.to_dict() if self.root else None

    def _replace_child(self, parent: Optional[Node], old: Node, new: Optional[Node]) -> None:
        if parent is None:
            self.root = new
        elif parent.left is old:
            parent.left = new
        else:
            parent.right = new
        if new is not None:
            new.parent = parent


# ======================================================================
# Red-black tree
# ======================================================================
def is_red(n: Optional[Node]) -> bool:
    return n is not None and n.color == RED


def is_black(n: Optional[Node]) -> bool:
    return n is None or n.color == BLACK  # NIL leaves are black


class RedBlackTree(BinarySearchTree):
    """
    Red-black rules (NIL leaves count as black):
      1. every node is red or black      2. the root is black
      3. a red node never has a red child
      4. every root-to-NIL path has the same number of black nodes (= black height)
    """

    kind = "rb"

    def _after_load(self) -> None:
        for n in self._nodes():
            if n.color not in (RED, BLACK):
                raise TreeFormatError("Every node of a red-black tree needs a color.")
        problem = self.violation()
        if problem:
            raise TreeFormatError(f"Not a valid red-black tree: {problem}")

    def violation(self) -> Optional[str]:
        """None if all red-black rules hold, otherwise a short description."""
        if self.root is None:
            return None
        if self.root.color != BLACK:
            return "the root is red."
        depths: set[int] = set()

        def walk(n: Optional[Node], d: int) -> Optional[str]:
            if n is None:
                depths.add(d)
                return None
            if is_red(n) and (is_red(n.left) or is_red(n.right)):
                return f"red node {fmt(n.value)} has a red child."
            d += n.color == BLACK
            return walk(n.left, d) or walk(n.right, d)

        err = walk(self.root, 0)
        if err:
            return err
        if len(depths) > 1:
            return "root-to-NIL paths have different black depths."
        return None

    def black_height(self) -> int:
        h, n = 0, self.root
        while n is not None:
            h += n.color == BLACK
            n = n.left
        return h

    # ---------------------------------------------------------- rotations
    def _rotate_left(self, x: Node) -> None:
        y = x.right
        x.right = y.left
        if y.left:
            y.left.parent = x
        self._replace_child(x.parent, x, y)
        y.left = x
        x.parent = y

    def _rotate_right(self, x: Node) -> None:
        y = x.left
        x.left = y.right
        if y.right:
            y.right.parent = x
        self._replace_child(x.parent, x, y)
        y.right = x
        x.parent = y

    def _rotate(self, at: Node, direction: str) -> None:
        (self._rotate_left if direction == "left" else self._rotate_right)(at)

    # ------------------------------------------------------------ build
    def insert(self, value: float) -> Optional[Node]:
        """BST insert, then repair the rules (no steps — used to build the tree)."""
        z = super().insert(value)
        if z is None:
            return None
        z.color = RED
        self._insert_fixup(z)
        return z

    def _insert_fixup(self, z: Node) -> None:
        while z.parent is not None and z.parent.color == RED:
            p = z.parent
            g = p.parent  # exists: a red node is never the root
            p_side = "left" if g.left is p else "right"
            u = g.right if p_side == "left" else g.left  # uncle
            if is_red(u):  # case 1: recolor and continue higher up
                p.color = u.color = BLACK
                g.color = RED
                z = g
                continue
            if (p.left is z) != (p_side == "left"):  # case 2: inner child → rotate at p
                self._rotate(p, p_side)
                z, p = p, z
            p.color, g.color = BLACK, RED  # case 3: rotate at the grandparent
            self._rotate(g, "right" if p_side == "left" else "left")
        self.root.color = BLACK


# ======================================================================
# Graph
# ======================================================================
INF = math.inf
H_SCALE = 50  # screen pixels per 1 unit of distance for the A* / greedy heuristic


class GraphError(ValueError):
    """Bad input (shown to the user as a 400 error)."""


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
