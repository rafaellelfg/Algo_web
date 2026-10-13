"""Red-Black tree with step-by-step algorithms.

Red-black rules (NIL leaves count as black):
  1. every node is red or black
  2. the root is black
  3. a red node never has a red child
  4. every path from the root down to a NIL leaf has the same number of
     black nodes (the "black depth" of that path = the black height of the tree)

Algorithms here, each returning a list of steps for the frontend:
  * insert_steps       BST insert + fix-up (cases 1–3)
  * delete_steps       BST delete + double-black fix-up (cases 1–4)
  * black_depth_steps  walk every root→NIL path, check the rules
  * paint_steps        try to colour an existing plain BST as a red-black tree
"""
from __future__ import annotations

from typing import Optional

from .bst import BLACK, RED, BinarySearchTree, Node, TreeFormatError, fmt


def is_red(n: Optional[Node]) -> bool:
    return n is not None and n.color == RED


def is_black(n: Optional[Node]) -> bool:
    return n is None or n.color == BLACK  # NIL leaves are black


def _name(n: Optional[Node]) -> str:
    return fmt(n.value) if n is not None else "NIL"


def _fmt_set(s: set[int]) -> str:
    return "{" + ",".join(str(x) for x in sorted(s)) + "}" if s else "∅"


class RedBlackTree(BinarySearchTree):
    kind = "rb"

    # ------------------------------------------------------------ loading
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

    # ------------------------------------------------------------- insert
    def insert(self, value: float) -> Optional[Node]:
        """Insert without steps (used to build the tree)."""
        node = super().insert(value)
        if node is not None:
            node.color = RED
            self._insert_fixup(node, None)
        return node

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
        self._insert_fixup(z, steps)
        steps.append(
            self._step(
                f"{fmt(target)} inserted. All red-black rules hold — black height {self.black_height()}.", code="done",
                status="done",
                changed=z.id,
            )
        )
        return True, steps

    def _insert_fixup(self, z: Node, steps: Optional[list[dict]]) -> None:
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

    # ------------------------------------------------------------- delete
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

        # Removing a red node never changes a black depth
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

        # Removing the root
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

        # Black node with a red child: the child takes over the black
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

        # Black node with no red child: a "double black" appears
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
            # the recursion stack of visit(): shown with the current call (top) first
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
def paint_steps(tree: BinarySearchTree) -> tuple[bool, list[dict], Optional[RedBlackTree]]:
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

    rb = RedBlackTree.from_dict(tree.snapshot())  # validates the result
    steps.append(
        rb._step(
            f"Painted! The same tree is now a valid red-black tree with black height {rb.black_height()}.", code="done",
            status="found",
        )
    )
    return True, steps, rb
