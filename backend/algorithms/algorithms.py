
from __future__ import annotations

import heapq
import math
from typing import Any, Optional

from .build import (
    BLACK,
    H_SCALE,
    INF,
    RED,
    BinarySearchTree,
    Graph,
    GraphError,
    Node,
    RedBlackTree,
    TreeFormatError,
    fmt,
    is_black,
    is_red,
)

__all__ = ["BSTAlgorithms", "RedBlackAlgorithms", "TREE_CLASSES", "paint_steps", "build_tree",
           "ALGORITHMS", "run", "cycle_check", "Graph", "GraphError", "TreeFormatError"]


# ======================================================================
# Trees: binary search tree
# ======================================================================
class BSTAlgorithms(BinarySearchTree):
    """A binary search tree plus its step-by-step search / insert / delete."""

    def _step(self, message: str, status: str = "info", code: Optional[str] = None, **highlight: Any) -> dict:
       
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

    def _successor_steps(self, node: Node, steps: list[dict], **extra: Any) -> Node:
        
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


# ======================================================================
# Trees: red-black tree
# ======================================================================
def _name(n: Optional[Node]) -> str:
    return fmt(n.value) if n is not None else "NIL"


def _fmt_set(s: set[int]) -> str:
    return "{" + ",".join(str(x) for x in sorted(s)) + "}" if s else "∅"


class RedBlackAlgorithms(BSTAlgorithms, RedBlackTree):
    """A red-black tree plus its step-by-step insert / delete / black depth (search comes from the BST)."""

    def insert_steps(self, target: float) -> tuple[bool, list[dict]]:
        steps: list[dict] = []
        z = self._insert_walk(target, steps)
        if z is None:
            return False, steps
        z.color = RED
        steps.append(
            self._step(
                f"A new node is always red (it doesn't change any black depth). Now check the red-black rules.", code="red",
                current=z.id,
                labels={z.id: "Z"},
            )
        )
        self._insert_fixup_steps(z, steps)
        steps.append(
            self._step(
                f"{fmt(target)} inserted. All red-black rules hold — black height {self.black_height()}.", code="done",
                status="done",
                changed=z.id,
            )
        )
        return True, steps

    def _insert_fixup_steps(self, z: Node, steps: list[dict]) -> None:
        rec = steps is not None
        while z.parent is not None and z.parent.color == RED:
            p = z.parent
            g = p.parent  # exists: a red node is never the root
            p_side = "left" if g.left is p else "right"
            u = g.right if p_side == "left" else g.left
            roles = {z.id: "Z", p.id: "P", g.id: "G"}
            if u:
                roles[u.id] = "U"

            if is_red(u):
                if rec:
                    steps.append(
                        self._step(
                            f"{_name(z)} and its parent {_name(p)} are both red. The uncle {_name(u)} is red too → "
                            f"Case 1: recolor — {_name(p)} and {_name(u)} become black, the grandparent "
                            f"{_name(g)} becomes red. Then check again from {_name(g)}.", code="case1",
                            current=z.id,
                            labels=roles,
                        )
                    )
                p.color = u.color = BLACK
                g.color = RED
                z = g
                continue

            z_side = "left" if p.left is z else "right"
            if z_side != p_side:
                if rec:
                    steps.append(
                        self._step(
                            f"{_name(z)} and its parent {_name(p)} are both red, the uncle {_name(u)} is black, and "
                            f"{_name(z)} is an inner child → Case 2: rotate {p_side} at {_name(p)} so it becomes "
                            f"an outer child (then Case 3).", code="case2",
                            current=z.id,
                            labels=roles,
                        )
                    )
                self._rotate(p, p_side)
                z, p = p, z
                roles = {z.id: "Z", p.id: "P", g.id: "G"}
                if u:
                    roles[u.id] = "U"

            other = "right" if p_side == "left" else "left"
            if rec:
                steps.append(
                    self._step(
                        f"{_name(z)} and its parent {_name(p)} are both red, the uncle {_name(u)} is black, and "
                        f"{_name(z)} is an outer child → Case 3: color {_name(p)} black and {_name(g)} red, "
                        f"then rotate {other} at {_name(g)}.", code="case3",
                        current=z.id,
                        labels=roles,
                    )
                )
            p.color = BLACK
            g.color = RED
            self._rotate(g, other)

        if self.root.color == RED:
            if rec:
                steps.append(
                    self._step(
                        f"The root {_name(self.root)} is red → color it black (rule 2: the root is always black).", code="root",
                        current=self.root.id,
                    )
                )
            self.root.color = BLACK

    def delete_steps(self, target: float) -> tuple[bool, list[dict]]:
        steps: list[dict] = []
        node, _ = self._search_walk(target, steps)
        if node is None:
            steps[-1]["message"] += " Nothing to delete."
            return False, steps

        v = fmt(node.value)
        if node.left is not None and node.right is not None:
            steps.append(
                self._step(
                    f"{v} has two children → copy its in-order successor into it, then remove the successor's "
                    f"old node instead (that node has at most one child).", code="two",
                    remove=node.id,
                )
            )
            succ = self._successor_steps(node, steps)
            s = fmt(succ.value)
            node.value = succ.value
            steps.append(
                self._step(
                    f"Copy {s} into the node that held {v} (that node keeps its color). Now remove the old {s} node.", code="copy",
                    changed=node.id,
                    successor=succ.id,
                )
            )
            y = succ
        else:
            y = node

        yv = fmt(y.value)
        x = y.left or y.right
        x_parent = y.parent
        x_side = None if x_parent is None else ("left" if x_parent.left is y else "right")
        child_txt = f"one child ({fmt(x.value)})" if x else "no children"

        
        if y.color == RED:
            steps.append(
                self._step(
                    f"The node to remove ({yv}) is red and has {child_txt} → removing a red node doesn't change any "
                    f"black depth. Just remove it.", code="red",
                    remove=y.id,
                )
            )
            self._replace_child(x_parent, y, x)
            self.size -= 1
            steps.append(self._step(f"{v} deleted. No fix-up needed.", status="done", code="done", changed=x.id if x else None))
            return True, steps

        
        if x_parent is None:
            steps.append(
                self._step(
                    f"The node to remove ({yv}) is the root with {child_txt} → "
                    + (f"{fmt(x.value)} becomes the new root and is colored black." if x else "the tree becomes empty."),
                    code="remove",
                    remove=y.id,
                )
            )
            self._replace_child(None, y, x)
            self.size -= 1
            if x:
                x.color = BLACK
            steps.append(self._step(f"{v} deleted.", status="done", code="done", changed=x.id if x else None))
            return True, steps

        
        if is_red(x):
            steps.append(
                self._step(
                    f"The node to remove ({yv}) is black, but its child {fmt(x.value)} is red → put "
                    f"{fmt(x.value)} in its place and color it black. Every black depth stays the same.", code="redchild",
                    remove=y.id,
                    changed=x.id,
                )
            )
            self._replace_child(x_parent, y, x)
            x.color = BLACK
            self.size -= 1
            steps.append(self._step(f"{v} deleted. No further fix-up needed.", status="done", code="done", changed=x.id))
            return True, steps

        
        steps.append(
            self._step(
                f"The node to remove ({yv}) is black and has {child_txt} → after removing it, every path through "
                f"this spot is one black node short. The spot becomes \"double black\" (DB) and must be fixed.", code="db",
                remove=y.id,
            )
        )
        self._replace_child(x_parent, y, x)
        self.size -= 1
        self._delete_fixup(x, x_parent, x_side, steps)
        steps.append(
            self._step(
                f"{v} deleted. All red-black rules hold — black height {self.black_height()}.", code="done",
                status="done",
            )
        )
        return True, steps

    def _db(self, x: Optional[Node], x_parent: Optional[Node], x_side: Optional[str]) -> dict:
        """Highlight for the double-black spot (a real node or an empty NIL slot)."""
        if x is not None:
            return {"current": x.id, "labels": {x.id: "DB"}}
        return {"missing": {"parent": x_parent.id, "side": x_side, "label": "DB"}}

    def _delete_fixup(self, x: Optional[Node], x_parent: Optional[Node], x_side: Optional[str], steps: list[dict]) -> None:
        resolved = False
        while x is not self.root and is_black(x):
            far_side = "right" if x_side == "left" else "left"
            w = x_parent.right if x_side == "left" else x_parent.left  # sibling — never NIL here
            near = w.left if x_side == "left" else w.right
            far = w.right if x_side == "left" else w.left
            hl = self._db(x, x_parent, x_side)
            labels = {**hl.get("labels", {}), x_parent.id: "P", w.id: "W"}
            hl["labels"] = labels
            db_name = _name(x)

            if is_red(w):
                steps.append(
                    self._step(
                        f"Double black at {db_name}. Its sibling {_name(w)} is red → Case 1: color {_name(w)} black and "
                        f"the parent {_name(x_parent)} red, then rotate {x_side} at {_name(x_parent)}. "
                        f"Now the sibling is black (one of cases 2–4 follows).", code="d1",
                        **hl,
                    )
                )
                w.color = BLACK
                x_parent.color = RED
                self._rotate(x_parent, x_side)
                continue

            if is_black(w.left) and is_black(w.right):
                steps.append(
                    self._step(
                        f"Double black at {db_name}. Its sibling {_name(w)} is black with two black children → "
                        f"Case 2: color {_name(w)} red and move the double black up to the parent {_name(x_parent)}.", code="d2",
                        **hl,
                    )
                )
                w.color = RED
                x = x_parent
                x_parent = x.parent
                x_side = None if x_parent is None else ("left" if x_parent.left is x else "right")
                continue

            if is_black(far):
                steps.append(
                    self._step(
                        f"Double black at {db_name}. Its sibling {_name(w)} is black, the sibling's far child "
                        f"({_name(far)}) is black and the near child ({_name(near)}) is red → Case 3: color "
                        f"{_name(near)} black and {_name(w)} red, then rotate {far_side} at {_name(w)} (→ Case 4).", code="d3",
                        **hl,
                    )
                )
                near.color = BLACK
                w.color = RED
                self._rotate(w, far_side)
                continue

            steps.append(
                self._step(
                    f"Double black at {db_name}. Its sibling {_name(w)} is black and the sibling's far child "
                    f"({_name(far)}) is red → Case 4: {_name(w)} takes the parent's color, {_name(x_parent)} and "
                    f"{_name(far)} become black, then rotate {x_side} at {_name(x_parent)}. The double black is gone.", code="d4",
                    **hl,
                )
            )
            w.color = x_parent.color
            x_parent.color = BLACK
            far.color = BLACK
            self._rotate(x_parent, x_side)
            resolved = True
            break

        if resolved or x is None:
            return
        if x.color == RED:
            steps.append(
                self._step(
                    f"The double black reached {fmt(x.value)}, which is red → just color it black. "
                    f"The missing black node is restored.", code="dfinal",
                    current=x.id,
                    labels={x.id: "DB"},
                )
            )
            x.color = BLACK
        elif x is self.root:
            steps.append(
                self._step(
                    f"The double black reached the root ({fmt(x.value)}) → it can simply be dropped: every path "
                    f"lost one black node, so they are all equal again.", code="dfinal",
                    current=x.id,
                    labels={x.id: "DB"},
                )
            )

    # -------------------------------------------------------- black depth
    def black_depth_steps(self) -> tuple[bool, list[dict], Optional[int]]:
        """
        Walk the tree from the root and compute the black depth of every node
        (number of black nodes from the root down to it). At every NIL leaf the
        path's black depth is recorded; all of them must be equal.
        """
        steps: list[dict] = []
        if self.root is None:
            steps.append(self._step("The tree is empty: black height 0.", status="found", code="result"))
            return True, steps, 0

        labels: dict[int, str] = {}
        nil_depths: list[int] = []
        problems: list[str] = []

        root_ok = self.root.color == BLACK
        if not root_ok:
            problems.append("the root is red")
        steps.append(
            self._step(
                "Black depth of a node = how many black nodes lie on the path from the root down to it "
                "(red nodes don't count). Rule 2: the root must be black → "
                f"root {fmt(self.root.value)} is {self.root.color} {'✓' if root_ok else '✗'}.", code="root",
                current=self.root.id,
                path=[self.root.id],
            )
        )

        def call_stack(frames: list[str]) -> dict:
            
            return {"type": "stack", "title": "Call stack of visit() (top first)", "items": [{"label": f} for f in reversed(frames)]}

        def visit(n: Node, above: int, path: list[int], frames: list[str]) -> None:
            path = path + [n.id]
            frames = frames + [f"visit({fmt(n.value)}, depth={above})"]
            d = above + (1 if n.color == BLACK else 0)
            labels[n.id] = str(d)
            how = f"black → +1 = {d}" if n.color == BLACK else f"red → stays {d}"
            msg = f"{fmt(n.value)} is {how}."
            if is_red(n) and is_red(n.parent):
                problems.append(f"red {fmt(n.value)} has a red parent {fmt(n.parent.value)}")
                msg += f" ✗ It has a red parent ({fmt(n.parent.value)}) — rule 3 is broken."
            steps.append(self._step(msg, code="node", current=n.id, path=path, labels=dict(labels), ds=call_stack(frames)))

            for side in ("left", "right"):
                child = n.left if side == "left" else n.right
                if child is not None:
                    visit(child, d, path, frames)
                else:
                    nil_depths.append(d)
                    steps.append(
                        self._step(
                            f"NIL ({side} of {fmt(n.value)}): this root-to-NIL path has black depth {d}.", code="nil",
                            path=path,
                            labels=dict(labels),
                            missing={"parent": n.id, "side": side, "label": "NIL"},
                            ds=call_stack(frames + [f"visit(NIL, depth={d})"]),
                        )
                    )

        visit(self.root, 0, [], [])

        distinct = sorted(set(nil_depths))
        if len(distinct) > 1:
            problems.append(f"root-to-NIL paths have different black depths {distinct}")

        if problems:
            steps.append(
                self._step(
                    "Not a valid red-black tree: " + "; ".join(problems) + ".", code="result",
                    status="not_found",
                    labels=dict(labels),
                )
            )
            return False, steps, None

        bh = distinct[0]
        steps.append(
            self._step(
                f"All {len(nil_depths)} root-to-NIL paths have black depth {bh}, the root is black and no red node "
                f"has a red child → valid red-black tree with black height {bh}.", code="result",
                status="found",
                labels=dict(labels),
            )
        )
        return True, steps, bh



# ---------------------------------------------------------------- painting
def paint_steps(tree: BinarySearchTree) -> tuple[bool, list[dict], Optional[RedBlackAlgorithms]]:
    """
    Try to colour an existing BST (same shape!) as a red-black tree.

    Bottom-up, for every node compute which black heights its subtree can have
      B = possible black heights if the node is black  = {h+1 : h possible for both children}
      R = possible black heights if the node is red    = {h   : h possible for both children *as black*}
    (a NIL leaf has black height 0 and is black). The root must be black, so the
    tree can be painted iff B(root) is not empty. Then colour top-down.
    """
    steps: list[dict] = []
    if tree.root is None:
        steps.append(tree._step("The tree is empty — nothing to paint.", status="not_found", code="fail"))
        return False, steps, None

    for n in tree._nodes():
        n.color = None
    B: dict[int, set[int]] = {}
    R: dict[int, set[int]] = {}
    labels: dict[int, str] = {}

    def any_color(n: Optional[Node]) -> set[int]:
        return {0} if n is None else B[n.id] | R[n.id]

    def as_black(n: Optional[Node]) -> set[int]:
        return {0} if n is None else B[n.id]

    steps.append(
        tree._step(
            "Goal: give every node a color so that all red-black rules hold, without changing the shape. "
            "Bottom-up, compute for each node the possible black heights of its subtree: "
            "B = if the node is black, R = if it is red (NIL leaves have black height 0).", code="start",
        )
    )

    postorder: list[Node] = []

    def collect(n: Optional[Node]) -> None:
        if n:
            collect(n.left)
            collect(n.right)
            postorder.append(n)

    collect(tree.root)

    for n in postorder:
        both_any = any_color(n.left) & any_color(n.right)
        B[n.id] = {h + 1 for h in both_any}
        R[n.id] = as_black(n.left) & as_black(n.right)
        labels[n.id] = f"B {_fmt_set(B[n.id])}\nR {_fmt_set(R[n.id])}"  # two lines in the badge
        v = fmt(n.value)
        if not B[n.id] and not R[n.id]:
            steps.append(
                tree._step(
                    f"{v}: its left subtree can only have black height {_fmt_set(any_color(n.left))} and its right "
                    f"subtree only {_fmt_set(any_color(n.right))} — no common value. The paths below {v} can never "
                    f"have equal black depth, so this BST cannot be painted as a red-black tree "
                    f"(it is too unbalanced).", code="fail",
                    status="not_found",
                    current=n.id,
                    labels=dict(labels),
                )
            )
            for m in tree._nodes():
                m.color = None
            return False, steps, None
        kids = "both children are NIL" if not (n.left or n.right) else (
            f"children allow {_fmt_set(both_any)} (any color) and {_fmt_set(R[n.id])} (both black)"
        )
        steps.append(
            tree._step(
                f"{v}: {kids} → if black, black height ∈ {_fmt_set(B[n.id])}; if red, ∈ {_fmt_set(R[n.id])}.", code="sets",
                current=n.id,
                labels=dict(labels),
            )
        )

    root = tree.root
    target = max(B[root.id])
    steps.append(
        tree._step(
            f"The root must be black: possible black heights {_fmt_set(B[root.id])}. Choose {target}. "
            f"Now color top-down.", code="choose",
            current=root.id,
            labels=dict(labels),
        )
    )

    queue: list[tuple[Node, str, int]] = [(root, BLACK, target)]

    def queue_ds() -> dict:
        return {
            "type": "queue",
            "title": "Queue of nodes to color",
            "items": [{"label": f"{fmt(q.value)} → {c}", "detail": f"bh {hh}"} for q, c, hh in queue],
        }

    while queue:
        ds_before = queue_ds()
        n, color, h = queue.pop(0)
        n.color = color
        labels[n.id] = f"bh {h}"
        if color == BLACK:
            why = "black"
            child_h = h - 1
            for c in (n.left, n.right):
                if c is not None:
                    queue.append((c, BLACK if child_h in B[c.id] else RED, child_h))
        else:
            why = "red (so both its children must be black)"
            for c in (n.left, n.right):
                if c is not None:
                    queue.append((c, BLACK, h))
        steps.append(
            tree._step(
                f"Take {fmt(n.value)} from the front of the queue and color it {why}; its subtree has black height {h}.",
                code="color",
                changed=n.id,
                labels=dict(labels),
                ds={**ds_before, "active": 0},
            )
        )

    rb = RedBlackAlgorithms.from_dict(tree.snapshot())  # validates the result
    steps.append(
        rb._step(
            f"Painted! The same tree is now a valid red-black tree with black height {rb.black_height()}.", code="done",
            status="found",
        )
    )
    return True, steps, rb


TREE_CLASSES = {"bst": BSTAlgorithms, "rb": RedBlackAlgorithms}


def build_tree(values: list[float]) -> tuple[BSTAlgorithms, list[float]]:
    """Build a plain BST (with its algorithms) from a list. Returns (tree, skipped duplicates)."""
    return BSTAlgorithms.build(values)


# ======================================================================
# Graphs
# ======================================================================
def _num(x: float) -> str:
    if x == INF:
        return "∞"
    if x == -INF:
        return "-∞"
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def step(message: str, code: str, status: str = "info", ds: Optional[dict] = None, **hl: Any) -> dict:
    """One step of a graph algorithm."""
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

    steps.append(step(
        f"Start at {g.n(start)}: mark it visited and put it in the queue. "
        "BFS explores the graph level by level (by number of edges).",
        "init", current=start, visited=list(visited), frontier=list(queue), labels=labels(), ds=_queue(g, queue),
    ))
    while queue:
        node = queue[0]
        steps.append(step(
            f"Take {g.n(node)} from the front of the queue.", "pop",
            current=node, visited=list(visited), frontier=list(queue), labels=labels(), ds=_queue(g, queue, active=0),
        ))
        queue.pop(0)
        order.append(node)
        if node == goal:
            p = g.path(parent, goal)
            steps.append(step(
                f"{g.n(goal)} reached! Path with the fewest edges: {g.path_text(p)} ({len(p) - 1} edge(s)).",
                "found", status="found", current=node, visited=list(visited), path_nodes=p, path_edges=g.pairs(p),
                labels=labels(), ds=_queue(g, queue),
            ))
            return {"ok": True, "outcome": f"FOUND · {len(p) - 1} EDGE(S)", "steps": steps, "path": p}
        for nb, _ in g.adj[node]:
            if nb in level:
                steps.append(step(
                    f"Edge {g.e(node, nb)}: {g.n(nb)} was already visited → skip.", "skip",
                    current=node, active_edge=[node, nb], visited=list(visited), frontier=list(queue),
                    labels=labels(), ds=_queue(g, queue),
                ))
                continue
            visited.append(nb)
            parent[nb] = node
            level[nb] = level[node] + 1
            queue.append(nb)
            steps.append(step(
                f"Edge {g.e(node, nb)}: {g.n(nb)} is new → mark it visited (distance {level[nb]}) "
                f"and add it to the back of the queue.",
                "push", current=node, active_edge=[node, nb], visited=list(visited), frontier=list(queue),
                labels=labels(), ds=_queue(g, queue, active=len(queue) - 1),
            ))
    if goal is not None:
        steps.append(step(
            f"The queue is empty and {g.n(goal)} was never reached → there is no path from {g.n(start)}.",
            "done", status="not_found", visited=list(visited), labels=labels(), ds=_queue(g, []),
        ))
        return {"ok": False, "outcome": "NOT REACHABLE", "steps": steps}
    steps.append(step(
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

    steps.append(step(
        f"Put {g.n(start)} on the stack. DFS always continues from the most recently found node, "
        "going as deep as possible before backtracking.",
        "init", current=start, frontier=list(stack), ds=ds(),
    ))
    while stack:
        steps.append(step(
            f"Pop {g.n(stack[-1])} from the top of the stack.", "pop",
            current=stack[-1], visited=list(visited), frontier=list(stack), ds=ds(active=0),
        ))
        node = stack.pop()
        if node in visited:
            steps.append(step(
                f"{g.n(node)} was already visited → ignore this stack entry.", "skip",
                current=node, visited=list(visited), frontier=list(stack), ds=ds(),
            ))
            continue
        visited.append(node)
        tree_edges = [[parent[i], i] for i in visited if parent.get(i) is not None]
        steps.append(step(
            f"Visit {g.n(node)} (number {len(visited)} in the DFS order).", "visit",
            current=node, visited=list(visited), frontier=list(stack), path_edges=tree_edges, ds=ds(),
        ))
        if node == goal:
            p = g.path(parent, goal)
            steps.append(step(
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
            steps.append(step(
                f"Edge {g.e(node, nb)}: {g.n(nb)} not visited yet → push it on the stack.", "push",
                current=node, active_edge=[node, nb], visited=list(visited), frontier=list(stack),
                path_edges=tree_edges, ds=ds(active=0),
            ))
    tree_edges = [[parent[i], i] for i in visited if parent.get(i) is not None]
    if goal is not None:
        steps.append(step(
            f"The stack is empty and {g.n(goal)} was never reached → there is no path from {g.n(start)}.",
            "done", status="not_found", visited=list(visited), path_edges=tree_edges, ds=ds(),
        ))
        return {"ok": False, "outcome": "NOT REACHABLE", "steps": steps}
    steps.append(step(
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

    steps.append(step(
        f"Set every distance to ∞ except {g.n(start)} = 0, and put ({g.n(start)}, 0) in the priority queue.",
        "init", current=start, labels=_dist_labels(g, dist), frontier=[start], ds=ds(),
    ))
    while heap:
        d, node = heap[0]
        steps.append(step(
            f"Take the entry with the smallest distance: {g.n(node)} ({_num(d)}).", "pop",
            current=node, visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(active=True),
        ))
        heapq.heappop(heap)
        if node in done:
            steps.append(step(
                f"{g.n(node)} is already final — this is an old, outdated entry → skip it.", "skip",
                current=node, visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
            ))
            continue
        done.append(node)
        steps.append(step(
            f"{g.n(node)} is now final: its shortest distance is {_num(d)}.", "final",
            current=node, visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
        ))
        if node == goal:
            p = g.path(prev, goal)
            steps.append(step(
                f"{g.n(goal)} is final → shortest path {g.path_text(p)} with total weight {_num(dist[goal])}.",
                "found", status="found", current=node, visited=list(done), labels=_dist_labels(g, dist),
                path_nodes=p, path_edges=g.pairs(p), ds=ds(),
            ))
            return {"ok": True, "outcome": f"DISTANCE {_num(dist[goal])}", "steps": steps, "path": p}
        for nb, w in g.adj[node]:
            if nb in done:
                steps.append(step(
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
                steps.append(step(
                    f"Edge {g.e(node, nb)} (weight {_num(w)}): {_num(d)} + {_num(w)} = {_num(new)} < {_num(old)} → "
                    f"relax: distance of {g.n(nb)} becomes {_num(new)}, push ({g.n(nb)}, {_num(new)}).",
                    "relax", current=node, active_edge=[node, nb], visited=list(done), labels=_dist_labels(g, dist),
                    path_edges=tree_edges(), ds=ds(),
                ))
            else:
                steps.append(step(
                    f"Edge {g.e(node, nb)} (weight {_num(w)}): {_num(d)} + {_num(w)} = {_num(new)} ≥ {_num(dist[nb])} → "
                    f"no improvement.",
                    "norelax", current=node, active_edge=[node, nb], visited=list(done), labels=_dist_labels(g, dist),
                    path_edges=tree_edges(), ds=ds(),
                ))
    if goal is not None:
        steps.append(step(
            f"The priority queue is empty and {g.n(goal)} is still ∞ → not reachable from {g.n(start)}.",
            "done", status="not_found", visited=list(done), labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
        ))
        return {"ok": False, "outcome": "NOT REACHABLE", "steps": steps}
    reach = [f"{g.n(i)}={_num(dist[i])}" for i in g.ids]
    steps.append(step(
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

    steps.append(step(
        f"Greedy best-first search only looks at h = straight-line distance to {g.n(goal)} "
        f"(screen distance / {H_SCALE}). Put {g.n(start)} in the priority queue.",
        "init", current=start, labels=hl, frontier=[start], ds=ds(),
    ))
    while heap:
        hv, node = heap[0]
        steps.append(step(
            f"Take the node that looks closest to the goal: {g.n(node)} (h={_num(hv)}).", "pop",
            current=node, visited=list(visited), labels=hl, path_edges=tree_edges(), ds=ds(active=True),
        ))
        heapq.heappop(heap)
        if node in visited:
            steps.append(step(f"{g.n(node)} was already expanded → skip.", "skip",
                                current=node, visited=list(visited), labels=hl, ds=ds()))
            continue
        visited.append(node)
        if node == goal:
            p = g.path(parent, goal)
            c = g.cost(p)
            steps.append(step(
                f"{g.n(goal)} reached! Path {g.path_text(p)} with total weight {_num(c)}. Greedy search is fast, "
                f"but this is not guaranteed to be the shortest path.",
                "found", status="found", current=node, visited=list(visited), labels=hl,
                path_nodes=p, path_edges=g.pairs(p), ds=ds(),
            ))
            return {"ok": True, "outcome": f"FOUND · COST {_num(c)}", "steps": steps, "path": p}
        for nb, _ in g.adj[node]:
            if nb in visited or nb in parent:
                steps.append(step(
                    f"Edge {g.e(node, nb)}: {g.n(nb)} is already known → skip.", "skip",
                    current=node, active_edge=[node, nb], visited=list(visited), labels=hl, path_edges=tree_edges(), ds=ds(),
                ))
                continue
            parent[nb] = node
            heapq.heappush(heap, (g.h(nb, goal), nb))
            steps.append(step(
                f"Edge {g.e(node, nb)}: add {g.n(nb)} with h={_num(g.h(nb, goal))}.", "push",
                current=node, active_edge=[node, nb], visited=list(visited), labels=hl, path_edges=tree_edges(), ds=ds(),
            ))
    steps.append(step(
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

    steps.append(step(
        f"A* orders nodes by f = g + h: g = distance travelled so far, h = straight-line estimate to {g.n(goal)} "
        f"(screen distance / {H_SCALE}). Start: g({g.n(start)}) = 0.",
        "init", current=start, labels=labels(), frontier=[start], ds=ds(),
    ))
    while heap:
        f, gv, node = heap[0]
        steps.append(step(
            f"Take the node with the smallest f: {g.n(node)} (f = {_num(gv)} + {_num(g.h(node, goal))} = {_num(f)}).",
            "pop", current=node, visited=list(closed), labels=labels(), path_edges=tree_edges(), ds=ds(active=True),
        ))
        heapq.heappop(heap)
        if node in closed:
            steps.append(step(f"{g.n(node)} is already closed — outdated entry → skip.", "skip",
                                current=node, visited=list(closed), labels=labels(), path_edges=tree_edges(), ds=ds()))
            continue
        if node == goal:
            closed.append(node)
            p = g.path(prev, goal)
            steps.append(step(
                f"{g.n(goal)} reached! Shortest path {g.path_text(p)} with total weight {_num(gs[goal])}.",
                "found", status="found", current=node, visited=list(closed), labels=labels(),
                path_nodes=p, path_edges=g.pairs(p), ds=ds(),
            ))
            return {"ok": True, "outcome": f"DISTANCE {_num(gs[goal])}", "steps": steps, "path": p}
        closed.append(node)
        steps.append(step(f"Close {g.n(node)} and look at its neighbours.", "close",
                            current=node, visited=list(closed), labels=labels(), path_edges=tree_edges(), ds=ds()))
        for nb, w in g.adj[node]:
            if nb in closed:
                steps.append(step(
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
                steps.append(step(
                    f"Edge {g.e(node, nb)} (weight {_num(w)}): g({g.n(nb)}) = {_num(gs[node])} + {_num(w)} = {_num(new_g)}, "
                    f"f = {_num(new_g)} + {_num(g.h(nb, goal))} = {_num(fv)} → push.",
                    "relax", current=node, active_edge=[node, nb], visited=list(closed), labels=labels(),
                    path_edges=tree_edges(), ds=ds(),
                ))
            else:
                steps.append(step(
                    f"Edge {g.e(node, nb)}: {_num(new_g)} is not better than g({g.n(nb)}) = {_num(gs[nb])} → skip.",
                    "norelax", current=node, active_edge=[node, nb], visited=list(closed), labels=labels(),
                    path_edges=tree_edges(), ds=ds(),
                ))
    steps.append(step(
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
    steps.append(step(
        f"Set every distance to ∞ except {g.n(start)} = 0. Then relax all {len(edges)} edges{extra}, "
        f"up to {len(g.ids) - 1} rounds (number of nodes − 1).",
        "init", current=start, labels=_dist_labels(g, dist), ds=ds(start),
    ))
    rounds = max(len(g.ids) - 1, 0)
    for r in range(1, rounds + 1):
        changed = 0
        steps.append(step(f"Round {r}: go through every edge once.", "round",
                            labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds()))
        for u, v, w in edges:
            if dist[u] == INF or dist[u] + w >= dist[v]:
                continue  # nothing to do (not shown, to keep the steps short)
            old = dist[v]
            dist[v] = dist[u] + w
            prev[v] = u
            changed += 1
            if len(steps) < MAX_BF_STEPS:
                steps.append(step(
                    f"Round {r}, edge {g.e(u, v)} (weight {_num(w)}): {_num(dist[u])} + {_num(w)} = {_num(dist[v])} "
                    f"< {_num(old)} → relax: distance of {g.n(v)} = {_num(dist[v])}.",
                    "relax", current=v, active_edge=[u, v], labels=_dist_labels(g, dist),
                    path_edges=tree_edges(), ds=ds(v),
                ))
        if changed == 0:
            steps.append(step(
                f"Round {r}: no distance changed → the distances are final, stop early.", "early",
                labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds(),
            ))
            break
        steps.append(step(f"Round {r} finished: {changed} distance(s) improved.", "round",
                            labels=_dist_labels(g, dist), path_edges=tree_edges(), ds=ds()))

    steps.append(step(
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
            steps.append(step(
                f"Edge {g.e(u, v)} can still be relaxed → NEGATIVE CYCLE {g.path_text(cycle)} "
                f"(total weight {_num(total)}). Going around it again and again makes the distance smaller forever, "
                f"so shortest paths are not defined.",
                "negcycle", status="not_found", active_edge=[u, v], cycle_nodes=cycle[:-1],
                cycle_edges=g.pairs(cycle), labels=_dist_labels(g, dist), ds=ds(),
            ))
            return {"ok": False, "outcome": "NEGATIVE CYCLE", "steps": steps, "cycle": cycle}

    reach = [f"{g.n(i)}={_num(dist[i])}" for i in g.ids]
    steps.append(step(
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

    steps.append(step(
        "Count the incoming edges (in-degree) of every node. Nodes with in-degree 0 have nothing before them, "
        f"so they can go first: {g.names_of(queue) or 'none'}.",
        "zero", labels=labels(), frontier=list(queue), ds=_queue(g, queue),
    ))
    while queue:
        u = queue[0]
        steps.append(step(
            f"Take {g.n(u)} from the queue and append it to the order.", "pop",
            current=u, visited=list(order), labels=labels(), frontier=list(queue), ds=_queue(g, queue, active=0),
        ))
        queue.pop(0)
        order.append(u)
        for v, _ in g.adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
                steps.append(step(
                    f"Remove edge {g.e(u, v)}: in-degree of {g.n(v)} drops to 0 → add it to the queue.", "push",
                    current=u, active_edge=[u, v], visited=list(order), labels=labels(), frontier=list(queue),
                    ds=_queue(g, queue, active=len(queue) - 1),
                ))
            else:
                steps.append(step(
                    f"Remove edge {g.e(u, v)}: in-degree of {g.n(v)} drops to {indeg[v]}.", "edge",
                    current=u, active_edge=[u, v], visited=list(order), labels=labels(), frontier=list(queue),
                    ds=_queue(g, queue),
                ))
    if len(order) < len(g.ids):
        rest = [i for i in g.ids if i not in order]
        steps.append(step(
            f"The queue is empty but {g.names_of(rest)} still have incoming edges → they lie on a CYCLE. "
            "A graph with a cycle has no topological order.",
            "cycle", status="not_found", visited=list(order), cycle_nodes=rest, labels=labels(), ds=_queue(g, []),
        ))
        return {"ok": False, "outcome": "HAS A CYCLE", "steps": steps}
    steps.append(step(
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
            steps.append(step(
                f"Visit {g.n(u)}" + (" — it is now GRAY (on the current path)." if g.directed else "."),
                "visit", ds=ds(), **hl(current=u),
            ))
        for v, _ in g.adj[u]:
            if not g.directed and v == parent:
                if rec:
                    steps.append(step(
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
                    steps.append(step(
                        f"Edge {g.e(u, v)}: {why} → CYCLE {g.path_text(cyc)}.",
                        "cycle", status="not_found", ds=ds(),
                        **hl(current=u, active_edge=[u, v], cycle_nodes=cyc[:-1], cycle_edges=g.pairs(cyc)),
                    ))
                return True
            if color[v] == WHITE:
                if rec:
                    steps.append(step(
                        f"Edge {g.e(u, v)}: {g.n(v)} not visited yet → go deeper.",
                        "descend", ds=ds(), **hl(current=u, active_edge=[u, v]),
                    ))
                if visit(v, u):
                    return True
            elif rec:  # directed and BLACK
                steps.append(step(
                    f"Edge {g.e(u, v)}: {g.n(v)} is BLACK (fully explored earlier) → no cycle through it.",
                    "skip", ds=ds(), **hl(current=u, active_edge=[u, v]),
                ))
        color[u] = BLACK
        stack_nodes.pop()
        frames.pop()
        if rec:
            steps.append(step(
                f"All edges of {g.n(u)} checked → {g.n(u)} is finished" + (" (BLACK)." if g.directed else "."),
                "finish", ds=ds(), **hl(current=u),
            ))
        return False

    if rec:
        intro = ("Directed graph: DFS colors nodes WHITE (new), GRAY (on the current path), BLACK (finished). "
                 "An edge to a GRAY node closes a cycle.") if g.directed else (
                 "Undirected graph: DFS remembers each node's parent. Reaching an already visited node that is "
                 "not the parent closes a cycle.")
        steps.append(step(intro, "init", ds=ds()))

    components = 0
    for s in g.ids:
        if color[s] != WHITE:
            continue
        components += 1
        if rec:
            steps.append(step(f"Start a new DFS from {g.n(s)}.", "start", ds=ds(), **hl(current=s)))
        if visit(s, None):
            cyc = found[0]
            return {
                "ok": False, "outcome": "CYCLIC", "steps": steps,
                "cyclic": True, "cycle": cyc, "cycle_text": g.path_text(cyc),
            }

    if rec:
        msg = ("No back edge found → the graph is ACYCLIC (a DAG)." if g.directed else
               f"No cycle found → the graph is ACYCLIC (a forest of {components} tree(s)).")
        steps.append(step(msg, "done", status="found", ds=ds(), **hl()))
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
