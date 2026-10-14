import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Fine for a local/learning project. In production set these as environment variables.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-change-me-binary-tree-demo")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
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
TOKEN_HASH_KEY = os.environ.get("TOKEN_HASH_KEY", SECRET_KEY)
TOKEN_TTL = {
    "user": timedelta(hours=12),
    "admin": timedelta(minutes=30),  # admin keys live much shorter
}
MAX_ACTIVE_TOKENS_PER_USER = 10

# Admin login = password + the admin phrase. Only its PBKDF2 hash is stored here.
# Default phrase: IB002. New hash: python manage.py hash_phrase "NEW PHRASE"
ADMIN_PHRASE_HASH = os.environ.get(
    "ADMIN_PHRASE_HASH",
    "pbkdf2_sha256$310000$9f1c2b7e4d8a6035b1e2c3d4a5f60718$yDoF0Or3/hIAx6X4x5DVd8Dl0SLHoqvgtQOEsJD1lNM=",
)
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
