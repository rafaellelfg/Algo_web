"""Binary Search Tree (BST) with step-by-step search, insert and delete.

Rule: smaller values go to the left subtree, larger values to the right.
Duplicates are not inserted (they are returned separately).

Every node has a stable integer ``id`` so the frontend can highlight
exactly the node a step refers to (values can repeat temporarily during
deletion, ids never do).

Nodes also keep a ``parent`` pointer and an optional ``color`` so that the
Red-Black tree (rbtree.py) can reuse this class.
"""
from __future__ import annotations

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

    # ---------------------------------------------------------------- steps
    def _step(self, message: str, status: str = "info", code: Optional[str] = None, **highlight: Any) -> dict:
        """
        One step of an algorithm: explanation + tree state + what to highlight.
        `code` is a tag that tells the frontend which line of the Python code
        (see code.py) is running in this step.
        """
        ds = highlight.pop("ds", None)  # optional helper data structure (stack / queue)
        step = {
            "message": message,
            "status": status,  # info | found | not_found | done
            "code": code,
            "tree": self.snapshot(),
            "highlight": {k: v for k, v in highlight.items() if v is not None},
        }
        if ds is not None:
            step["ds"] = ds
        return step

    def _walk(self, target: float, steps: list[dict], purpose: str) -> tuple[Optional[Node], Optional[Node], str]:
        """
        Shared walk from the root towards `target`, recording compare steps.
        Returns (node, parent, side): node is the match (or None), and for a
        miss `parent`/`side` tell where the value would be attached.
        """
        if self.root is None:
            return None, None, "root"

        path: list[int] = []
        parent: Optional[Node] = None
        current: Optional[Node] = self.root
        steps.append(
            self._step(f"Start at the root ({fmt(self.root.value)}).", code="start", current=self.root.id, path=[self.root.id])
        )

        while current is not None:
            path.append(current.id)
            t, v = fmt(target), fmt(current.value)

            if target == current.value:
                found_msg = "node found." if purpose != "insert" else f"{t} is already in the tree."
                steps.append(
                    self._step(
                        f"Compare {t} with {v}: they are equal → {found_msg}",
                        status="found" if purpose != "insert" else "not_found",
                        code="equal",
                        current=current.id,
                        path=list(path),
                        found=current.id,
                    )
                )
                return current, parent, "dup"

            side = "left" if target < current.value else "right"
            sign = "<" if side == "left" else ">"
            child = current.left if side == "left" else current.right

            if child is None:
                tail = "→ this is where it goes." if purpose == "insert" else ""
                steps.append(
                    self._step(
                        f"Compare {t} with {v}: {t} {sign} {v} → go {side}, "
                        f"but the {side} child of {v} is empty {tail}".rstrip(),
                        code=f"attach_{side}" if purpose == "insert" else side,
                        current=current.id,
                        path=list(path),
                        missing={"parent": current.id, "side": side, "label": "new" if purpose == "insert" else "null"},
                    )
                )
                return None, current, side

            steps.append(
                self._step(
                    f"Compare {t} with {v}: {t} {sign} {v} → go to the {side} child ({fmt(child.value)}).",
                    code=side,
                    current=current.id,
                    path=list(path) + [child.id],
                    next=child.id,
                )
            )
            parent, current = current, child

        return None, None, "root"  # unreachable

    def _search_walk(self, target: float, steps: list[dict]) -> tuple[Optional[Node], Optional[Node]]:
        """Search walk; on a miss adds the final NOT FOUND step."""
        if self.root is None:
            steps.append(self._step("The tree is empty — there is nothing to search.", status="not_found", code="notfound"))
            return None, None
        node, parent, side = self._walk(target, steps, "search")
        if node is None:
            last = steps[-1]["highlight"]
            steps.append(
                self._step(
                    f"Reached an empty spot. {fmt(target)} is not in the tree.",
                    status="not_found",
                    code="notfound",
                    path=last.get("path"),
                    missing=last.get("missing"),
                )
            )
        return node, parent

    def search_steps(self, target: float) -> tuple[bool, list[dict]]:
        steps: list[dict] = []
        node, _ = self._search_walk(target, steps)
        return node is not None, steps

    def _insert_walk(self, target: float, steps: list[dict]) -> Optional[Node]:
        """Walk to the empty spot and attach a new node there (with steps)."""
        t = fmt(target)
        if self.root is None:
            steps.append(self._step(f"The tree is empty → {t} becomes the root.", code="empty"))
            return self._attach(target, None, "root")
        node, parent, side = self._walk(target, steps, "insert")
        if node is not None:
            steps[-1]["message"] += " Nothing to insert."
            return None
        new = self._attach(target, parent, side)
        steps.append(
            self._step(
                f"Insert {t} as the {side} child of {fmt(parent.value)}.",
                code=f"attach_{side}",
                changed=new.id,
                path=steps[-1]["highlight"].get("path", []) + [new.id],
            )
        )
        return new

    def insert_steps(self, target: float) -> tuple[bool, list[dict]]:
        steps: list[dict] = []
        new = self._insert_walk(target, steps)
        if new is not None:
            steps.append(
                self._step(f"{fmt(target)} inserted. The tree now has {self.size} node(s).", status="done", code="done", changed=new.id)
            )
        return new is not None, steps

    def _replace_child(self, parent: Optional[Node], old: Node, new: Optional[Node]) -> None:
        if parent is None:
            self.root = new
        elif parent.left is old:
            parent.left = new
        else:
            parent.right = new
        if new is not None:
            new.parent = parent

    def _successor_steps(self, node: Node, steps: list[dict], **extra: Any) -> Node:
        """Walk to the smallest node of the right subtree, recording steps."""
        v = fmt(node.value)
        succ = node.right
        path = [succ.id]
        steps.append(
            self._step(
                f"Go to the right child of {v}: {fmt(succ.value)}.",
                code="succ_right",
                remove=node.id,
                current=succ.id,
                path=list(path),
                **extra,
            )
        )
        while succ.left is not None:
            steps.append(
                self._step(
                    f"{fmt(succ.value)} has a left child → go left to {fmt(succ.left.value)}.",
                    code="succ_left",
                    remove=node.id,
                    current=succ.left.id,
                    path=list(path) + [succ.left.id],
                    **extra,
                )
            )
            succ = succ.left
            path.append(succ.id)
        s = fmt(succ.value)
        steps.append(
            self._step(
                f"{s} has no left child → {s} is the in-order successor.",
                code="succ",
                remove=node.id,
                successor=succ.id,
                path=list(path),
                **extra,
            )
        )
        return succ

    def delete_steps(self, target: float) -> tuple[bool, list[dict]]:
        steps: list[dict] = []
        node, parent = self._search_walk(target, steps)
        if node is None:
            steps[-1]["message"] += " Nothing to delete."
            return False, steps

        v = fmt(node.value)
        where = f"its parent ({fmt(parent.value)})" if parent else "the root position"

        # Case 1: leaf
        if node.left is None and node.right is None:
            steps.append(
                self._step(f"Case 1: {v} is a leaf (no children) → simply remove it.", code="case1", remove=node.id)
            )
            self._replace_child(parent, node, None)
            self.size -= 1
            steps.append(
                self._step(
                    f"{v} removed. The tree now has {self.size} node(s).",
                    status="done",
                    code="done",
                    changed=parent.id if parent else None,
                )
            )
            return True, steps

        # Case 2: exactly one child
        if node.left is None or node.right is None:
            child = node.left or node.right
            side = "left" if node.left else "right"
            steps.append(
                self._step(
                    f"Case 2: {v} has only a {side} child ({fmt(child.value)}) → "
                    f"connect {fmt(child.value)} directly to {where}.",
                    code="case2",
                    remove=node.id,
                    changed=child.id,
                )
            )
            self._replace_child(parent, node, child)
            self.size -= 1
            steps.append(
                self._step(
                    f"{v} removed, {fmt(child.value)} took its place. The tree now has {self.size} node(s).",
                    status="done",
                    code="done",
                    changed=child.id,
                )
            )
            return True, steps

        # Case 3: two children → in-order successor
        steps.append(
            self._step(
                f"Case 3: {v} has two children → replace it with its in-order successor "
                f"(the smallest value in the right subtree).",
                code="case3",
                remove=node.id,
            )
        )
        succ = self._successor_steps(node, steps)
        s = fmt(succ.value)
        node.value = succ.value
        steps.append(
            self._step(
                f"Copy {s} into the node that held {v}. Now {s} appears twice — remove the old {s} node.",
                code="copy",
                changed=node.id,
                successor=succ.id,
            )
        )

        succ_parent = succ.parent
        if succ.right is not None:
            msg = f"The old {s} node has a right child ({fmt(succ.right.value)}) → connect it to {fmt(succ_parent.value)}."
        else:
            msg = f"The old {s} node is a leaf → just remove it."
        steps.append(self._step(msg, code="remove_succ", remove=succ.id, changed=node.id))

        self._replace_child(succ_parent, succ, succ.right)
        self.size -= 1
        steps.append(
            self._step(
                f"{v} deleted and replaced by {s}. The tree now has {self.size} node(s).",
                status="done",
                code="done",
                changed=node.id,
            )
        )
        return True, steps


def build_tree(values: list[float]) -> tuple[BinarySearchTree, list[float]]:
    """Build a plain BST from a list. Returns the tree and the skipped duplicates."""
    return BinarySearchTree.build(values)
