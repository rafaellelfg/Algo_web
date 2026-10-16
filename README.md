# Algorithm Visualizer

Step-by-step visualizations of trees (BST, Red-Black) and graphs. The structure
is on the left, the running **Python code** on the right, and the helper data
structure (queue / stack / priority queue / table) underneath. **Practice** has
small tasks with a story: choose a data structure, then a task.
Backend: Django (Python). Frontend: TypeScript (Vite).

## Run

Needs **Python 3.10+** and **Node.js 18+**. From this folder:

```
python run.py
```

The first run creates the `.env` file with the secrets, `backend/venv`, installs
packages, sets up the database, runs `npm install`, then starts both servers and
opens http://localhost:5173. Ctrl+C stops everything.

| Command | What it does |
|---|---|
| `python run.py createadmin` | create another admin account |
| `python run.py test` | run the backend tests (Python) |
| `python run.py e2e` | run the browser tests (Playwright, see below) |
| `python run.py setup` | only install / migrate, don't start |

## Secrets: the `.env` file

All secrets are in **`.env`** in this folder: the admin username, password and
admin phrase, and the server keys (`DJANGO_SECRET_KEY`, `TOKEN_HASH_KEY`).
The first `python run.py` creates it with random values. `.env` is in
`.gitignore`, so it stays on your computer and never goes to GitHub, and no
secret is written in the code.

To change one, edit `.env` and restart `python run.py`; it also updates the
admin account. If you'd rather not keep the phrase itself, run
`backend/venv/Scripts/python backend/manage.py hash_phrase "PHRASE"`
(macOS/Linux: `backend/venv/bin/python`) and put the output into `.env` as
`ADMIN_PHRASE_HASH=…` instead of `ADMIN_SECRET_PHRASE`.

## Login and API keys

* **Users** sign up / log in → a **Bearer key** (`algo_u_…`), valid 12 h.
* **Admins** use **Log in → Admin login**: username + password, then the
  admin phrase (all three from `.env`) → an admin key (`algo_a_…`), valid 30 min.
  3 wrong phrases or 5 minutes and you start again. The same username and
  password open the database view at http://127.0.0.1:8000/admin/.
* Keys are dynamic: a new random key on each login, swapped for a fresh one
  before it expires, revoked on logout. The database stores only
  **HMAC-SHA256 hashes** of keys; the admin phrase is stored as a **PBKDF2** hash.
* "API key" (top right) shows your key, its expiry and a `curl` example:

```
curl -H "Authorization: Bearer <your key>" http://127.0.0.1:8000/api/history/
```

## Code layout

```
run.py                  one command to set up and start everything
backend/
  algorithms/
    build.py            builds the structures: BST, Red-Black tree, graph
    algorithms.py       runs the algorithms step by step (trees + graphs)
    code.py             the Python code shown next to each visualization
    practice.py         the Practice tasks: data structures and the task texts
  api/
    login.py            login, hash functions, Bearer keys, admin phrase
    api.py              all other endpoints: trees, history, graphs, admin
    models.py, urls.py  database tables, every URL
  tests/                python run.py test
frontend/src/           TypeScript pages (trees, graphs, practice, history, admin)
e2e/                    Playwright browser tests (TypeScript)
  tests/login.spec.ts   sign up, log in, Bearer keys, admin phrase, admin page
  tests/trees.spec.ts   BST + Red-Black: search, insert, delete, black depth, paint, history
  tests/graphs.spec.ts  sections, cycles parameter, BFS, DFS, Dijkstra, A*, Greedy, Bellman-Ford, topo sort
  tests/practice.spec.ts  choose a data structure → its tasks → one task
```

## Browser tests (Playwright)

```
python run.py e2e
```

This installs the test tools and Chromium once, then runs all tests; Playwright
starts the site by itself (or reuses it if `python run.py` is already running).
By hand: `cd e2e`, `npm install`, `npx playwright install chromium`, `npm test`.
`npm run test:ui` opens the interactive runner, `npm run report` the last report.
The admin tests create their own account `e2e_admin` (new random password each run)
and read the admin phrase from `.env`.

## API (all under `/api/`)

| | |
|---|---|
| `auth/register/`, `auth/login/` | → `{token, role, expires_at, user}` |
| `auth/admin/login/` → `auth/admin/verify/` | password → `{challenge_id}` → + `answer` (the admin phrase) → admin key |
| `auth/token/refresh/`, `auth/logout/`, `auth/tokens/` | rotate / revoke / list your keys |
| `tree/`, `tree/op/` | build a tree; run `search`, `insert`, `delete`, `paint`, `black_depth` |
| `history/…` | your saved trees and operations (needs a key) |
| `graph/analyze/`, `graph/run/` | cycle check; BFS, DFS, Dijkstra, Greedy, A*, Bellman-Ford, topological sort |
| `practice/`, `practice/<task>/` | the data structures with their tasks; one task (story, rules, input, output) |
| `admin/users/`, `admin/tokens/` | admins only: users, active keys, revoke |

