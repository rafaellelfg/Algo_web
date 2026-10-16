"""Start the whole project with one command:   python run.py

    python run.py               set up what is missing, then start backend + frontend
    python run.py setup         only set up (virtual env, packages, database, npm)
    python run.py createadmin   create another admin account (it logs in with "Admin login" + the phrase from .env)
    python run.py test          run the backend tests
    python run.py e2e           run the Playwright browser tests in ./e2e

Setup = the .env file with the secrets + backend/venv (Python virtual environment)
+ pip install + database migrations + the admin account + npm install.
Each part is skipped when it is already done. Stop the servers with Ctrl+C.
"""
from __future__ import annotations

import hashlib
import os
import secrets
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

# All secrets (admin account, admin phrase, server keys) live in .env, which is
# in .gitignore: it stays on this computer and never goes to GitHub.
ENV_FILE = ROOT / ".env"
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"


def say(msg: str) -> None:
    print(f">> {msg}", flush=True)


def run(cmd: list, cwd: Path) -> None:
    result = subprocess.run([str(c) for c in cmd], cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"Command failed: {' '.join(map(str, cmd))}")


def read_env() -> dict:
    """KEY=VALUE lines of .env (blank lines and # comments are skipped)."""
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]  # KEY="value" works too
                values[key.strip()] = value
    return values


def ensure_env() -> dict:
    """Create .env with fresh random secrets, or add the ones that are missing.
    Values that are already there are never changed."""
    env = read_env()
    fresh = {
        "ADMIN_USERNAME": f"admin{secrets.randbelow(9000) + 1000}",
        "ADMIN_PASSWORD": secrets.token_urlsafe(12),
        "ADMIN_SECRET_PHRASE": secrets.token_hex(4).upper(),
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
        "TOKEN_HASH_KEY": secrets.token_hex(32),
    }
    if env.get("ADMIN_PHRASE_HASH"):
        fresh.pop("ADMIN_SECRET_PHRASE")  # only the hash of the phrase is kept: fine
    missing = {k: v for k, v in fresh.items() if not env.get(k)}
    if not missing:
        return env

    if ENV_FILE.exists():
        text = ENV_FILE.read_text(encoding="utf-8-sig").rstrip("\n") + "\n\n# added by run.py\n"
        text += "".join(f"{k}={v}\n" for k, v in missing.items())
    else:
        text = (
            "# Secrets of this project. They stay on this computer: .env is in .gitignore,\n"
            "# so git never uploads this file to GitHub. Change a value, then restart `python run.py`.\n"
            "\n"
            "# Admin account. On the site: Log in -> Admin login -> username + password, then the phrase.\n"
            f"ADMIN_USERNAME={missing['ADMIN_USERNAME']}\n"
            f"ADMIN_PASSWORD={missing['ADMIN_PASSWORD']}\n"
            f"ADMIN_SECRET_PHRASE={missing['ADMIN_SECRET_PHRASE']}\n"
            "\n"
            "# Random server keys (Django signing + hashing of the API keys). Never share them.\n"
            f"DJANGO_SECRET_KEY={missing['DJANGO_SECRET_KEY']}\n"
            f"TOKEN_HASH_KEY={missing['TOKEN_HASH_KEY']}\n"
        )
    ENV_FILE.write_text(text, encoding="utf-8")
    say(f"Saved new secrets to .env: {', '.join(missing)}")
    if "ADMIN_PASSWORD" in missing:
        say("Your admin login, password and admin phrase are in the .env file.")
    return read_env()


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


def setup() -> dict:
    # 0. Secrets: the .env file (created with random values the first time)
    env = ensure_env()

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

    # 3. Database tables (does nothing when they are up to date) + the admin account from .env
    say("Updating the database...")
    run([VENV_PY, "manage.py", "migrate", "--noinput", "-v", "0"], BACKEND)
    run([VENV_PY, "manage.py", "ensure_admin"], BACKEND)

    # 4. Frontend packages (only again when package.json changed)
    pkg = FRONTEND / "package.json"
    nstamp = FRONTEND / "node_modules" / ".package.sha256"
    if not nstamp.exists() or nstamp.read_text() != file_hash(pkg):
        say("Installing frontend packages (npm install)...")
        run([npm(), "install", "--no-fund", "--no-audit"], FRONTEND)
        nstamp.write_text(file_hash(pkg))
    return env


def start() -> None:
    env = setup()
    say(f"Starting the backend  -> {BACKEND_URL}")
    backend = subprocess.Popen([str(VENV_PY), "manage.py", "runserver", "127.0.0.1:8000"], cwd=BACKEND)
    say(f"Starting the frontend -> {FRONTEND_URL}")
    frontend = subprocess.Popen([npm(), "run", "dev", "--", "--port", "5173", "--strictPort"], cwd=FRONTEND)
    procs = [backend, frontend]

    time.sleep(3)
    say(f"Open {FRONTEND_URL}   (Ctrl+C stops both servers)")
    say(f"Admin login: {env.get('ADMIN_USERNAME', '?')} (password and admin phrase: see the .env file)")
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
        say("Create an admin account (it can use 'Admin login' on the site with the phrase from .env).")
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
