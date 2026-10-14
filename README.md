# Algorithm Visualizer

Step-by-step visualizations of trees (BST, Red-Black) and graphs. The structure
is on the left, the running **Python code** on the right, and the helper data
structure (queue / stack / priority queue / table) underneath.
Backend: Django (Python). Frontend: TypeScript (Vite).

## Run

Needs **Python 3.10+** and **Node.js 18+**. From this folder:

```
python run.py
```

The first run creates `backend/venv`, installs packages, sets up the database,
runs `npm install`, then starts both servers and opens http://localhost:5173.
Ctrl+C stops everything.

| Command | What it does |
|---|---|
| `python run.py createadmin` | create another admin account |
| `python run.py test` | run the backend tests (Python) |
| `python run.py e2e` | run the browser tests (Playwright, see below) |
| `python run.py setup` | only install / migrate, don't start |

## Login and API keys

**Admin account** (created automatically by `python run.py`):

| Username | Password | Admin phrase |
|---|---|---|
| `admin` | `AlgoAdmin2026!` | `IB002` |

On the site: **Log in → Admin login** → username + password → then type the phrase.
The same username and password open the database view at http://127.0.0.1:8000/admin/.
Change the password there (or with `backend/venv/Scripts/python backend/manage.py changepassword admin`)
before putting the site anywhere public.

* **Users** sign up / log in → a **Bearer key** (`algo_u_…`), valid 12 h.
* **Admins** use **Admin login**: password, then the
  admin phrase **`IB002`** → an admin key (`algo_a_…`), valid 30 min.
  3 wrong phrases or 5 minutes and you start again.
* Keys are dynamic: a new random key on each login, swapped for a fresh one
  before it expires, revoked on logout. The database stores only
  **HMAC-SHA256 hashes** of keys; the admin phrase is stored as a **PBKDF2** hash.
* "API key" (top right) shows your key, its expiry and a `curl` example:

```
curl -H "Authorization: Bearer <your key>" http://127.0.0.1:8000/api/history/
```

Change the admin phrase: `backend/venv/Scripts/python backend/manage.py hash_phrase "NEW PHRASE"`
(macOS/Linux: `backend/venv/bin/python`) and put the output into the
`ADMIN_PHRASE_HASH` environment variable.

## Code layout

```
run.py                  one command to set up and start everything
backend/
  algorithms/
    build.py            builds the structures: BST, Red-Black tree, graph
    algorithms.py       runs the algorithms step by step (trees + graphs)
    code.py             the Python code shown next to each visualization
  api/
    login.py            login, hash functions, Bearer keys, admin phrase
    api.py              all other endpoints: trees, history, graphs, admin
    models.py, urls.py  database tables, every URL
  tests/                python run.py test
frontend/src/           TypeScript pages (trees, graphs, history, admin)
e2e/                    Playwright browser tests (TypeScript)
  tests/login.spec.ts   sign up, log in, Bearer keys, admin phrase, admin page
  tests/trees.spec.ts   BST + Red-Black: search, insert, delete, black depth, paint, history
  tests/graphs.spec.ts  sections, cycles parameter, BFS, DFS, Dijkstra, A*, Greedy, Bellman-Ford, topo sort
```

## Browser tests (Playwright)

```
python run.py e2e
```

This installs the test tools and Chromium once, then runs all tests; Playwright
starts the site by itself (or reuses it if `python run.py` is already running).
By hand: `cd e2e`, `npm install`, `npx playwright install chromium`, `npm test`.
`npm run test:ui` opens the interactive runner, `npm run report` the last report.
The admin tests create the account `e2e_admin` with `manage.py ensure_admin`.

## API (all under `/api/`)

| | |
|---|---|
| `auth/register/`, `auth/login/` | → `{token, role, expires_at, user}` |
| `auth/admin/login/` → `auth/admin/verify/` | password → `{challenge_id}` → + `answer: "IB002"` → admin key |
| `auth/token/refresh/`, `auth/logout/`, `auth/tokens/` | rotate / revoke / list your keys |
| `tree/`, `tree/op/` | build a tree; run `search`, `insert`, `delete`, `paint`, `black_depth` |
| `history/…` | your saved trees and operations (needs a key) |
| `graph/analyze/`, `graph/run/` | cycle check; BFS, DFS, Dijkstra, Greedy, A*, Bellman-Ford, topological sort |
| `admin/users/`, `admin/tokens/` | admins only: users, active keys, revoke |

