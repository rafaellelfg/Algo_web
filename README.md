# Algorithm Visualizer — Django API + TypeScript

Step-by-step visualizations of data-structure algorithms. On every page the
**left side shows the data structure**, the **right side shows the Python code**
with the line that is running highlighted, plus the explanation of each step.
Under the picture you see the helper data structure the algorithm uses
(queue, stack, priority queue or distance table).

**Trees** (`#/`)
* Binary search tree: search, insert, delete.
* Red-Black tree: search, insert (fix-up cases 1–3), delete (double-black
  cases 1–4), **black depth** (checks every root-to-NIL path).
* **Paint as Red-Black**: tries to colour an existing BST (same shape) as a
  valid red-black tree, or explains why it can't be done.

**Graphs** (`#/graphs`), separate *Undirected* and *Directed* tabs
* Name a node → **Create node** → a section for it appears, where you add
  weighted edges. Drag nodes to move them. Graphs are remembered in the browser.
* Parameter **Cycles: Allowed / Not allowed** — when not allowed, an edge that
  would close a cycle is refused. The current status (cyclic / acyclic, and
  which cycle) is always shown.
* Algorithms: cycle check, BFS, DFS, Dijkstra, Greedy best-first, A*,
  Bellman-Ford, topological sort. Requirements are noted for each one:
  Dijkstra and A* need weights ≥ 0, Bellman-Ford needs **no negative cycles**
  (and detects them), topological sort needs a directed graph with **no cycles**.

**Practice** (`#/practice`) — coming soon.

**Accounts & history.** Sign up (name, username, password) / log in (top-right).
Users live in the SQLite database `backend/db.sqlite3` (table `auth_user`), each
with an integer `id`. Passwords are stored only as salted PBKDF2 hashes — never
as plain text — and are never sent back to the frontend. While logged in, every
tree you build and every operation on it is saved. The **History** page lists
your trees and all their operations; **Open** loads a tree to keep working on
it, **Replay** plays a past operation step by step again.

```
algo_website/
├── backend/              Django
│   ├── config/           settings, urls, CORS, JSON API helpers (api.py)
│   ├── accounts/         register / login / logout (Django users + sessions)
│   ├── tree/
│   │   ├── bst.py        BinarySearchTree: search / insert / delete with steps
│   │   ├── rbtree.py     RedBlackTree: insert / delete fix-ups, black depth, paint
│   │   ├── code.py       the Python code shown next to each tree algorithm
│   │   ├── models.py     SavedTree, Operation (the history)
│   │   ├── views.py      tree + history endpoints
│   │   └── tests.py
│   └── graphs/
│       ├── algorithms.py BFS, DFS, Dijkstra, Greedy, A*, Bellman-Ford, topo sort, cycle check
│       ├── code.py       the Python code shown next to each graph algorithm
│       ├── views.py      graph endpoints
│       └── tests.py      compared against brute-force reference results
└── frontend/             Vite + TypeScript
    └── src/
        ├── api.ts        API calls (sends session cookie + CSRF token)
        ├── auth.ts       log in / sign up dialog, current user
        ├── visualizer.ts Trees page (BST / Red-Black)
        ├── graph.ts      Graphs page
        ├── codeview.ts   Python code panel with the running line highlighted
        ├── dsview.ts     queue / stack / priority queue / table panel
        ├── history.ts    History page
        ├── layout.ts     node coordinates
        ├── render.ts     SVG drawing + highlighting
        ├── player.ts     step-by-step player
        └── main.ts       start-up and routing (#/, #/graphs, #/practice, #/history)
```

## Running (Windows, two terminals)

**1. Backend**
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate        # creates / updates the database tables
python manage.py createsuperuser   # optional: an account for the admin panel
python manage.py runserver
```

**2. Frontend** (Node.js 18+)
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 — Vite proxies `/api` to Django, so both must be running.

**Looking inside the database:** http://127.0.0.1:8000/admin/ (log in with the
superuser) shows the tables *Users*, *Saved trees* and *Operations*.

## API

All POST/DELETE requests need the `X-CSRFToken` header (value of the `csrftoken`
cookie, which `GET /api/auth/me/` sets). Login is kept in a session cookie.

| Method | URL | Body | Returns |
|---|---|---|---|
| GET | `/api/auth/me/` | – | `user` or `null` |
| POST | `/api/auth/register/` | `{"name", "username", "password"}` | `user` (and logs in) |
| POST | `/api/auth/login/` | `{"username", "password"}` | `user` |
| POST | `/api/auth/logout/` | – | `user: null` |
| POST | `/api/tree/` | `{"values": [50, 30, 70], "kind": "bst"\|"rb", "save": true}` | `kind`, `root`, `size`, `height`, `traversals`, `duplicates`, `tree_id` |
| POST | `/api/tree/op/` | `{"op": "search"\|"insert"\|"delete"\|"paint"\|"black_depth", "kind", "tree", "target"?, "tree_id"?}` | `found`, `outcome`, `steps`, `code`, new tree |
| POST | `/api/graph/analyze/` | `{"directed", "nodes", "edges"}` | `cyclic`, `cycle`, `cycle_text` |
| POST | `/api/graph/run/` | `{"directed", "nodes", "edges", "algorithm", "start"?, "goal"?}` | `ok`, `outcome`, `steps`, `code` |
| POST | `/api/tree/search/` | `{"tree": <root>, "target": 30, "tree_id": 1}` | `found`, `steps`, `tree_id` |
| POST | `/api/tree/delete/` | `{"tree": <root>, "target": 30, "tree_id": 1}` | `found`, `steps`, new `root`, `size`, `height`, `traversals`, `tree_id` |
| GET | `/api/history/` | – | `user` + `trees` (`initial_values`, `user_id`, `operations`) |
| GET / DELETE | `/api/history/<id>/` | – | one tree / remove it |
| GET | `/api/history/<id>/operations/<op>/` | – | one operation with its `steps` |

`tree_id` is set only when logged in; then the operation is saved to the history
and, for a saved tree, the server uses its own stored copy of the tree.

`user` is always `{"id": 2, "username": "rafa", "name": "Rafael"}`.

Example `GET /api/history/`:
```json
{
  "user": { "id": 2, "username": "rafa", "name": "Rafael" },
  "trees": [{
    "id": 3, "user_id": 2,
    "initial_values": [50, 30, 70, 20, 40, 60, 80, 35, 65],
    "root": { ... current tree ... }, "size": 8,
    "operations": [
      { "id": 7, "kind": "create", "target": null, "found": null, "size_after": 9 },
      { "id": 8, "kind": "search", "target": 40,   "found": true, "size_after": 9 },
      { "id": 9, "kind": "delete", "target": 30,   "found": true, "size_after": 8 }
    ]
  }]
}
```

Each node: `{"id": 0, "value": 50, "left": {...} | null, "right": {...} | null}`

Each step:
```json
{
  "message": "Compare 35 with 50: 35 < 50 → go to the left child (30).",
  "status": "info | found | not_found | done",
  "tree": { ... tree at this step ... },
  "highlight": { "current": 0, "path": [0, 1], "found": 4, "remove": 2,
                 "successor": 5, "changed": 0, "missing": {"parent": 3, "side": "right"} }
}
```

Deletion covers all three cases: a leaf, a node with one child, and a node with
two children (replaced by its in-order successor).

Backend tests: `python manage.py test`
