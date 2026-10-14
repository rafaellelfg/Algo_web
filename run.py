"""Start the whole project with one command:   python run.py

    python run.py               set up what is missing, then start backend + frontend
    python run.py setup         only set up (virtual env, packages, database, npm)
    python run.py createadmin   create another admin account (then use "Admin login" + phrase IB002)
    python run.py test          run the backend tests
    python run.py e2e           run the Playwright browser tests in ./e2e

Setup = backend/venv (Python virtual environment) + pip install + database
migrations + npm install. Each part is skipped when it is already done.
Stop the servers with Ctrl+C.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
E2E = ROOT / "e2e"
VENV = BACKEND / "venv"
WINDOWS = os.name == "nt"
VENV_PY = VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")

# Default admin account, created on the first setup (only if it does not exist yet).
# Admin login on the site: this username + password, then the admin phrase IB002.
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "AlgoAdmin2026!"
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"


def say(msg: str) -> None:
    print(f">> {msg}", flush=True)


def run(cmd: list, cwd: Path) -> None:
    result = subprocess.run([str(c) for c in cmd], cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"Command failed: {' '.join(map(str, cmd))}")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def npx() -> str:
    exe = shutil.which("npx")
    if not exe:
        sys.exit("npx was not found. Install Node.js 18 or newer from https://nodejs.org and try again.")
    return exe


def e2e() -> None:
    """Install the test tools once, then run the browser tests (Playwright starts the servers)."""
    setup()
    pkg = E2E / "package.json"
    nstamp = E2E / "node_modules" / ".package.sha256"
    if not nstamp.exists() or nstamp.read_text() != file_hash(pkg):
        say("Installing the test tools (npm install in e2e/)...")
        run([npm(), "install", "--no-fund", "--no-audit"], E2E)
        nstamp.write_text(file_hash(pkg))
    bstamp = E2E / "node_modules" / ".browser-installed"
    if not bstamp.exists():
        say("Downloading the test browser (Chromium, only once)...")
        run([npx(), "playwright", "install", "chromium"], E2E)
        bstamp.write_text("ok")
    say("Running the browser tests...")
    env = {**os.environ, "PYTHON": sys.executable}  # Playwright starts the servers with this same Python
    extra = [a for a in sys.argv[2:]]
    result = subprocess.run([npx(), "playwright", "test", *extra], cwd=E2E, env=env)
    say("Report: cd e2e && npx playwright show-report")
    sys.exit(result.returncode)


def npm() -> str:
    exe = shutil.which("npm")
    if not exe:
        sys.exit("npm was not found. Install Node.js 18 or newer from https://nodejs.org and try again.")
    return exe


def setup() -> None:
    # 1. Python virtual environment
    if not VENV_PY.exists():
        say("Creating the Python virtual environment (backend/venv)...")
        venv.EnvBuilder(with_pip=True).create(VENV)

    # 2. Python packages (only again when requirements.txt changed)
    req = BACKEND / "requirements.txt"
    stamp = VENV / ".requirements.sha256"
    if not stamp.exists() or stamp.read_text() != file_hash(req):
        say("Installing Python packages...")
        run([VENV_PY, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", req], BACKEND)
        stamp.write_text(file_hash(req))

    # 3. Database tables (does nothing when they are up to date)
    say("Updating the database...")
    run([VENV_PY, "manage.py", "migrate", "--noinput", "-v", "0"], BACKEND)
    run([VENV_PY, "manage.py", "ensure_admin", DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, "--if-missing"], BACKEND)

    # 4. Frontend packages (only again when package.json changed)
    pkg = FRONTEND / "package.json"
    nstamp = FRONTEND / "node_modules" / ".package.sha256"
    if not nstamp.exists() or nstamp.read_text() != file_hash(pkg):
        say("Installing frontend packages (npm install)...")
        run([npm(), "install", "--no-fund", "--no-audit"], FRONTEND)
        nstamp.write_text(file_hash(pkg))


def start() -> None:
    setup()
    say(f"Starting the backend  -> {BACKEND_URL}")
    backend = subprocess.Popen([str(VENV_PY), "manage.py", "runserver", "127.0.0.1:8000"], cwd=BACKEND)
    say(f"Starting the frontend -> {FRONTEND_URL}")
    frontend = subprocess.Popen([npm(), "run", "dev", "--", "--port", "5173", "--strictPort"], cwd=FRONTEND)
    procs = [backend, frontend]

    time.sleep(3)
    say(f"Open {FRONTEND_URL}   (Ctrl+C stops both servers)")
    say(f"Admin login: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}, admin phrase IB002")
    if "--no-browser" not in sys.argv:
        webbrowser.open(FRONTEND_URL)
    try:
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
        say("One of the servers stopped - stopping the other one too.")
    except KeyboardInterrupt:
        print()
        say("Stopping...")
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


def main() -> None:
    command = next((a for a in sys.argv[1:] if not a.startswith("--")), "start")
    if command == "start":
        start()
    elif command == "setup":
        setup()
        say("Setup done. Start with:  python run.py")
    elif command == "createadmin":
        setup()
        say("Create an admin account (it can use 'Admin login' on the site with the phrase IB002).")
        run([VENV_PY, "manage.py", "createsuperuser"], BACKEND)
    elif command == "test":
        setup()
        run([VENV_PY, "manage.py", "test"], BACKEND)
    elif command == "e2e":
        e2e()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
