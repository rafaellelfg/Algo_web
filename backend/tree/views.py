"""Tree API.

Anyone can build trees and run operations. If the user is logged in, every
tree and every operation is also saved to their history.

POST   /api/tree/                         {"values": [5, 3, 8], "kind": "bst"|"rb", "save": true?}
POST   /api/tree/op/                      {"op": ..., "kind": ..., "tree": {...}, "target": 3?, "tree_id": 7?}
          op = search | insert | delete           (both kinds)
               paint                              (bst: try to color it as a red-black tree)
               black_depth                        (rb: check black depths / black height)
POST   /api/tree/search/, /api/tree/delete/       shortcuts for op=search / op=delete
GET    /api/history/                      list of my trees with their operations
GET    /api/history/<id>/                 one tree
DELETE /api/history/<id>/                 remove a tree from my history
GET    /api/history/<id>/operations/<op>/ one operation with its steps (for replay)
"""
import math
from typing import Any, Optional

from django.db import transaction

from config.api import BadRequest, NotFound, api_view

from .bst import BinarySearchTree, fmt
from .code import code_for
from .models import Operation, SavedTree
from .rbtree import RedBlackTree, paint_steps

MAX_VALUES = 200
TREE_CLASSES = {"bst": BinarySearchTree, "rb": RedBlackTree}
OPS = {
    "bst": ("search", "insert", "delete", "paint"),
    "rb": ("search", "insert", "delete", "black_depth"),
}
NEEDS_TARGET = ("search", "insert", "delete")


def _normalize(n: Optional[float]) -> Optional[float]:
    """Send whole numbers as int (5, not 5.0)."""
    return int(n) if isinstance(n, float) and n.is_integer() else n


def _number(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise BadRequest(f"'{v}' is not a number.")
    return _normalize(v)


def _kind(v: Any) -> str:
    if v is None:
        return "bst"
    if v not in TREE_CLASSES:
        raise BadRequest("'kind' must be 'bst' or 'rb'.")
    return v


def _my_tree(request, tree_id: Any) -> Optional[SavedTree]:
    """The saved tree with this id if it belongs to the logged-in user, else None."""
    if not request.user.is_authenticated or tree_id is None:
        return None
    try:
        return SavedTree.objects.get(pk=int(tree_id), user=request.user)
    except (SavedTree.DoesNotExist, TypeError, ValueError):
        raise NotFound("This tree is not in your history.")


# ---------------------------------------------------------------- tree ops
@api_view()
def create_tree(request, data):
    values = data.get("values")
    if not isinstance(values, list) or not values:
        raise BadRequest("Send a non-empty array of numbers in the 'values' field.")
    if len(values) > MAX_VALUES:
        raise BadRequest(f"At most {MAX_VALUES} numbers are allowed.")
    kind = _kind(data.get("kind"))

    numbers = [_number(v) for v in values]
    tree, duplicates = TREE_CLASSES[kind].build(numbers)
    result = {**tree.summary(), "duplicates": duplicates, "tree_id": None}

    # "save": false lets the frontend build the demo tree without filling the history
    if request.user.is_authenticated and data.get("save", True) is not False:
        with transaction.atomic():
            saved = SavedTree.objects.create(
                user=request.user, kind=kind, initial_values=numbers, root=tree.snapshot(), size=tree.size
            )
            Operation.objects.create(
                tree=saved, kind=Operation.Kind.CREATE, tree_kind=kind, size_after=tree.size,
                outcome=f"{tree.size} NODES",
            )
        result["tree_id"] = saved.pk
    return result


def _outcome(op: str, ok: bool, target: Optional[float], extra: Any = None) -> str:
    t = fmt(target) if target is not None else ""
    return {
        "search": ("FOUND", "NOT FOUND"),
        "insert": (f"INSERTED {t}", "ALREADY IN TREE"),
        "delete": (f"DELETED {t}", "NOT FOUND"),
        "black_depth": (f"BLACK HEIGHT {extra}", "NOT VALID"),
        "paint": ("PAINTED", "CANNOT BE PAINTED"),
    }[op][0 if ok else 1]


def _run(request, data, op: str) -> dict:
    saved = _my_tree(request, data.get("tree_id"))
    # For a saved tree the database copy is the source of truth
    kind = saved.kind if saved else _kind(data.get("kind"))
    if op not in OPS[kind]:
        names = {"bst": "binary search tree", "rb": "red-black tree"}
        raise BadRequest(f"'{op}' is not available for a {names[kind]}.")

    target = None
    if op in NEEDS_TARGET:
        if "target" not in data:
            raise BadRequest("Send the value in the 'target' field.")
        target = _number(data["target"])

    tree = TREE_CLASSES[kind].from_dict(saved.root if saved else data.get("tree"))
    extra = None
    if op == "search":
        ok, steps = tree.search_steps(target)
    elif op == "insert":
        ok, steps = tree.insert_steps(target)
    elif op == "delete":
        ok, steps = tree.delete_steps(target)
    elif op == "black_depth":
        ok, steps, extra = tree.black_depth_steps()
    else:  # paint
        ok, steps, painted = paint_steps(tree)
        if ok:
            tree = painted

    changed = ok and op in ("insert", "delete", "paint")
    outcome = _outcome(op, ok, target, extra)
    result = {
        "operation": op,
        "target": target,
        "found": ok,
        "outcome": outcome,
        "steps": steps,
        "code": code_for(kind, op),
        **tree.summary(),  # the tree after the operation (kind becomes "rb" after painting)
    }

    if saved:
        with transaction.atomic():
            Operation.objects.create(
                tree=saved, kind=op, tree_kind=kind, target=target, found=ok, outcome=outcome,
                steps=steps, size_after=tree.size,
            )
            if changed:
                saved.root, saved.size, saved.kind = tree.snapshot(), tree.size, tree.kind
            saved.save()  # bumps updated_at so the tree moves to the top of the history
    result["tree_id"] = saved.pk if saved else None
    return result


@api_view()
def tree_op(request, data):
    op = data.get("op")
    if op not in ("search", "insert", "delete", "paint", "black_depth"):
        raise BadRequest("'op' must be one of: search, insert, delete, paint, black_depth.")
    return _run(request, data, op)


@api_view()
def search_node(request, data):
    return _run(request, data, "search")


@api_view()
def delete_node(request, data):
    return _run(request, data, "delete")


# ---------------------------------------------------------------- history
def _operation_json(op: Operation, with_steps: bool = False) -> dict:
    d = {
        "id": op.id,
        "kind": op.kind,
        "tree_kind": op.tree_kind,
        "target": _normalize(op.target),
        "found": op.found,
        "outcome": op.outcome,
        "size_after": op.size_after,
        "created_at": op.created_at.isoformat(),
    }
    if with_steps:
        d["steps"] = op.steps
        d["code"] = code_for(op.tree_kind, op.kind)
    return d


def _tree_json(t: SavedTree) -> dict:
    return {
        "id": t.pk,
        "user_id": t.user_id,
        "kind": t.kind,
        "initial_values": t.initial_values,
        "root": t.root,
        "size": t.size,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
        "operations": [_operation_json(op) for op in t.operations.all()],
    }


@api_view(methods=("GET",), login_required=True)
def history(request, data):
    trees = SavedTree.objects.filter(user=request.user).prefetch_related("operations")
    user = request.user
    return {
        "user": {"id": user.id, "username": user.username, "name": user.first_name or user.username},
        "trees": [_tree_json(t) for t in trees],
    }


@api_view(methods=("GET", "DELETE"), login_required=True)
def history_tree(request, data, tree_id: int):
    saved = _my_tree(request, tree_id)
    if request.method == "DELETE":
        saved.delete()
        return {"deleted": tree_id}
    summary = TREE_CLASSES[saved.kind].from_dict(saved.root).summary()
    return {"tree": {**_tree_json(saved), **summary}}


@api_view(methods=("GET",), login_required=True)
def history_operation(request, data, tree_id: int, op_id: int):
    saved = _my_tree(request, tree_id)
    try:
        op = saved.operations.get(pk=op_id)
    except Operation.DoesNotExist:
        raise NotFound("Operation not found.")
    return {"operation": _operation_json(op, with_steps=True)}
