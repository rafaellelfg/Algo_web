"""ALL API ENDPOINTS (except login, see login.py).

Trees
  POST   /api/tree/                  build a tree   {"values": [5, 3, 8], "kind": "bst"|"rb", "save"?}
                                     or save an existing one as it is  {"tree": {...}, "kind": ...}
  POST   /api/tree/op/               run an operation step by step
                                     {"op": search|insert|delete|paint|black_depth, "kind", "tree", "target"?, "tree_id"?}
  POST   /api/tree/search/, /api/tree/delete/       shortcuts for op=search / op=delete
History (needs a Bearer key)
  GET    /api/history/               my trees with their operations
  GET    /api/history/<id>/          one tree          DELETE /api/history/<id>/   remove it
  GET    /api/history/<id>/operations/<op>/          one operation with its steps (replay)
Graphs
  POST   /api/graph/analyze/         is the graph cyclic?   {"directed", "nodes", "edges"}
  POST   /api/graph/run/             run an algorithm step by step  {..., "algorithm", "start"?, "goal"?}
Practice
  GET    /api/practice/              the data structures (trees, graphs) with their tasks
  GET    /api/practice/<id>/         one task: story, task, rules, input and output
Admin (needs an ADMIN Bearer key)
  GET    /api/admin/users/           all users          GET /api/admin/tokens/   all active keys
  DELETE /api/admin/tokens/<id>/     revoke a key       DELETE /api/admin/users/<id>/tokens/   log a user out everywhere

The data structures and algorithms themselves are in ../algorithms/.
"""
import math
from typing import Any, Optional

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from algorithms import practice
from algorithms.algorithms import ALGORITHMS, TREE_CLASSES, Graph, cycle_check, paint_steps, run
from algorithms.build import fmt
from algorithms.code import graph_code, tree_code

from .core import BadRequest, NotFound, api_view
from .login import revoke, token_json, user_json
from .models import ApiToken, Operation, SavedTree


# ======================================================================
# Trees and history
# ======================================================================
MAX_VALUES = 200
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
    kind = _kind(data.get("kind"))
    if data.get("tree") is not None:

        tree = TREE_CLASSES[kind].from_dict(data["tree"])
        numbers, duplicates = tree._traverse("pre"), []
    else:
        values = data.get("values")
        if not isinstance(values, list) or not values:
            raise BadRequest("Send a non-empty array of numbers in the 'values' field.")
        if len(values) > MAX_VALUES:
            raise BadRequest(f"At most {MAX_VALUES} numbers are allowed.")
        numbers = [_number(v) for v in values]
        tree, duplicates = TREE_CLASSES[kind].build(numbers)
    result = {**tree.summary(), "duplicates": duplicates, "tree_id": None}

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
        "code": tree_code(kind, op),
        **tree.summary(),
    }

    if saved:
        with transaction.atomic():
            Operation.objects.create(
                tree=saved, kind=op, tree_kind=kind, target=target, found=ok, outcome=outcome,
                steps=steps, size_after=tree.size,
            )
            if changed:
                saved.root, saved.size, saved.kind = tree.snapshot(), tree.size, tree.kind
            saved.save()
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
        d["code"] = tree_code(op.tree_kind, op.kind)
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
    return {"user": user_json(request.user), "trees": [_tree_json(t) for t in trees]}


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


# ======================================================================
# Graphs (stateless: the frontend sends the whole graph every time)
# ======================================================================
def _graph(data: dict) -> Graph:
    return Graph(data.get("directed", False), data.get("nodes", []), data.get("edges", []))


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
    result = run(g, algorithm, data.get("start"), data.get("goal"))
    return {
        "algorithm": algorithm,
        "title": ALGORITHMS[algorithm][0],
        "code": graph_code(algorithm, g.directed),
        **result,
    }


# ======================================================================
# Practice tasks (their texts are in ../algorithms/practice.py)
# ======================================================================
@api_view(methods=("GET",))
def practice_tasks(request, data):
    return {"structures": practice.overview()}


@api_view(methods=("GET",))
def practice_task(request, data, task_id: str):
    task = practice.task_detail(task_id)
    if task is None:
        raise NotFound(f"There is no practice task '{task_id}'.")
    return {"task": task}


# ======================================================================
# Admin
# ======================================================================
@api_view(methods=("GET",), admin_required=True)
def admin_users(request, data):
    now = timezone.now()
    rows = User.objects.annotate(
        tree_count=Count("trees", distinct=True),
        active_keys=Count(
            "api_tokens",
            filter=Q(api_tokens__revoked_at__isnull=True, api_tokens__expires_at__gt=now),
            distinct=True,
        ),
    ).order_by("id")
    return {
        "users": [
            {
                **user_json(u),
                "date_joined": u.date_joined.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "trees": u.tree_count,
                "active_keys": u.active_keys,
            }
            for u in rows
        ]
    }


@api_view(methods=("GET",), admin_required=True)
def admin_tokens(request, data):
    rows = ApiToken.objects.select_related("user").filter(
        revoked_at__isnull=True, expires_at__gt=timezone.now()
    )
    return {"tokens": [{**token_json(r, request.auth), "user": user_json(r.user)} for r in rows]}


@api_view(methods=("DELETE",), admin_required=True)
def admin_revoke_token(request, data, token_id: int):
    try:
        row = ApiToken.objects.get(pk=token_id)
    except ApiToken.DoesNotExist:
        raise NotFound("Key not found.")
    revoke(row)
    return {"revoked": token_id}


@api_view(methods=("DELETE",), admin_required=True)
def admin_revoke_user_tokens(request, data, user_id: int):
    """Log a user out everywhere."""
    if not User.objects.filter(pk=user_id).exists():
        raise NotFound("User not found.")
    if user_id == request.user.id:
        raise BadRequest("To log yourself out everywhere, revoke your keys one by one.")
    count = ApiToken.objects.filter(user_id=user_id, revoked_at__isnull=True).update(revoked_at=timezone.now())
    return {"revoked": count}
