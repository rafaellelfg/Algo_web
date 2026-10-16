import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# ---- secrets: the .env file in the project folder ------------------------
# `python run.py` creates it with random values on the first start. It is in
# .gitignore, so the secrets stay on this computer and never go to GitHub.
# A real environment variable with the same name wins over the file.
ENV_FILE = BASE_DIR.parent / ".env"


def read_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines of a .env file (blank lines and # comments are skipped)."""
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key.strip()] = value
    return values


_ENV = read_env_file(ENV_FILE)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name) or _ENV.get(name, default)


def required_env(name: str) -> str:
    value = env(name)
    if not value:
        raise ImproperlyConfigured(
            f"{name} is missing. Start the project once with `python run.py`: it creates the .env file with the secrets."
        )
    return value


SECRET_KEY = required_env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",  # http://127.0.0.1:8000/admin/ — browse users, trees, operations
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "api",  # login.py + api.py (the data structures and algorithms are in ../algorithms/)
]

MIDDLEWARE = [
    "config.cors.SimpleCorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---- API authentication: "Authorization: Bearer <key>" -------------------
# Keys are random, short-lived and rotated by the frontend ("dynamic").
# The database stores only HMAC-SHA256 hashes of them (see api/login.py).
TOKEN_HASH_KEY = required_env("TOKEN_HASH_KEY")
TOKEN_TTL = {
    "user": timedelta(hours=12),
    "admin": timedelta(minutes=30),  # admin keys live much shorter
}
MAX_ACTIVE_TOKENS_PER_USER = 10

# Admin login = password + the admin phrase. Both come from .env:
#   ADMIN_USERNAME / ADMIN_PASSWORD  the admin account (run.py creates or updates it)
#   ADMIN_SECRET_PHRASE              the phrase; the server checks answers against its PBKDF2 hash
#   ADMIN_PHRASE_HASH                (optional) only the hash instead of the phrase:
#                                    python manage.py hash_phrase "PHRASE"
ADMIN_USERNAME = env("ADMIN_USERNAME")
ADMIN_PASSWORD = env("ADMIN_PASSWORD")
ADMIN_SECRET_PHRASE = env("ADMIN_SECRET_PHRASE")
ADMIN_PHRASE_HASH = env("ADMIN_PHRASE_HASH")
ADMIN_CHALLENGE_TTL = timedelta(minutes=5)
ADMIN_CHALLENGE_ATTEMPTS = 3

# Brute-force protection for logins
LOGIN_MAX_FAILURES = 10
LOGIN_LOCKOUT = timedelta(minutes=10)

# The Django admin site (/admin/) still uses its own session cookie + CSRF.
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# Origins allowed to call the API directly (the Vite dev server)
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
