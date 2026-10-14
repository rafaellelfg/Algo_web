"""LOGIN: users, passwords, Bearer keys and the admin phrase.

How it works
  * POST /api/auth/register/ or /api/auth/login/  (username + password)
        → a USER Bearer key, valid 12 hours
  * Admin login has two steps:
        POST /api/auth/admin/login/   username + password of a staff user → a one-time challenge
        POST /api/auth/admin/verify/  the challenge + the admin phrase ("IB002") → an ADMIN key, valid 30 minutes
  * Every request then sends   Authorization: Bearer <key>
  * Keys are "dynamic": each login makes a new random key, keys expire, and the
    frontend swaps its key for a fresh one (/api/auth/token/refresh/) before it runs out.
    Logging out revokes the key.

Sections of this file
  1. hash functions        2. Bearer keys        3. brute-force protection        4. endpoints
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User, update_last_login
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .core import BadRequest, Forbidden, NotFound, TooManyRequests, Unauthorized, api_view
from .models import AdminChallenge, ApiToken


# ======================================================================
# 1. Hash functions
#
# * API keys are long random strings (256 bits), so a fast keyed hash is enough:
#   HMAC-SHA256 with a server-side key ("pepper"). The database stores only this
#   hash — a leaked database does not leak usable keys.
# * The admin phrase is short and human-chosen ("IB002"), so it gets a slow,
#   salted hash: PBKDF2-HMAC-SHA256 with 310 000 iterations. Only the hash is kept.
# * Comparisons use hmac.compare_digest (constant time).
# ======================================================================
PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 310_000

TOKEN_PREFIX = {"user": "algo_u_", "admin": "algo_a_"}


# ------------------------------------------------------------- API keys
def new_token(role: str) -> str:
    """A fresh random API key, e.g. 'algo_u_Q2x…' (prefix shows the role)."""
    return TOKEN_PREFIX[role] + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """HMAC-SHA256(pepper, token) as 64 hex characters. One-way and deterministic,
    so a presented key can be looked up by its hash."""
    key = str(settings.TOKEN_HASH_KEY).encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------- admin phrase
def hash_phrase(phrase: str, salt: str | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Slow salted hash: 'pbkdf2_sha256$<iterations>$<salt>$<base64 hash>'."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", phrase.encode(), salt.encode(), iterations)
    return f"{PBKDF2_ALGORITHM}${iterations}${salt}${base64.b64encode(digest).decode()}"


def verify_phrase(phrase: str, encoded: str) -> bool:
    """Does `phrase` match the stored hash? (constant-time comparison)"""
    try:
        algorithm, iterations, salt, _ = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != PBKDF2_ALGORITHM:
        return False
    candidate = hash_phrase(phrase, salt, int(iterations))
    return hmac.compare_digest(candidate.encode(), encoded.encode())


def verify_admin_phrase(answer: str) -> bool:
    return verify_phrase(answer.strip(), settings.ADMIN_PHRASE_HASH)


# ======================================================================
# 2. Bearer keys
# ======================================================================
class TokenError(Exception):
    """The presented key is missing, unknown, expired or revoked."""


def issue_token(user, role: str = ApiToken.Role.USER, label: str = "") -> tuple[str, ApiToken]:
    """Create a new key for `user`. Returns (the key itself — shown once, the DB row)."""
    now = timezone.now()
    # housekeeping: drop dead keys and keep at most N active ones per user
    ApiToken.objects.filter(user=user, expires_at__lt=now - timedelta(days=7)).delete()
    active = ApiToken.objects.filter(user=user, revoked_at__isnull=True, expires_at__gt=now).order_by("-created_at")
    for old in active[settings.MAX_ACTIVE_TOKENS_PER_USER - 1:]:
        old.revoked_at = now
        old.save(update_fields=["revoked_at"])

    key = new_token(role)
    row = ApiToken.objects.create(
        user=user,
        role=role,
        key_hash=hash_token(key),
        prefix=key[:12],
        label=label[:40],
        expires_at=now + settings.TOKEN_TTL[role],
    )
    return key, row


def parse_authorization(header: Optional[str]) -> Optional[str]:
    """'Bearer abc' -> 'abc'; no header -> None; anything else -> TokenError."""
    if not header:
        return None
    scheme, _, key = header.partition(" ")
    if scheme.lower() != "bearer" or not key.strip():
        raise TokenError("Use the header 'Authorization: Bearer <your API key>'.")
    return key.strip()


def check_token(key: str) -> ApiToken:
    """Find the active key row for a presented key (by its hash)."""
    try:
        row = ApiToken.objects.select_related("user").get(key_hash=hash_token(key))
    except ApiToken.DoesNotExist:
        raise TokenError("Unknown API key. Log in again.")
    now = timezone.now()
    if row.revoked_at is not None:
        raise TokenError("This API key was revoked. Log in again.")
    if row.expires_at <= now:
        raise TokenError("Your API key expired. Log in again.")
    if not row.user.is_active:
        raise TokenError("This account is disabled.")
    if row.role == ApiToken.Role.ADMIN and not row.user.is_staff:
        raise TokenError("This account is no longer an admin.")
    # remember when it was used (at most once a minute, to avoid a write per request)
    if row.last_used_at is None or now - row.last_used_at > timedelta(minutes=1):
        row.last_used_at = now
        row.save(update_fields=["last_used_at"])
    return row


def revoke(row: ApiToken) -> None:
    if row.revoked_at is None:
        row.revoked_at = timezone.now()
        row.save(update_fields=["revoked_at"])


def token_json(row: ApiToken, current: Optional[ApiToken] = None) -> dict:
    return {
        "id": row.id,
        "prefix": row.prefix,
        "role": row.role,
        "label": row.label,
        "created_at": row.created_at.isoformat(),
        "expires_at": row.expires_at.isoformat(),
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        "active": row.is_active,
        "current": current is not None and row.id == current.id,
    }


# ======================================================================
# 3. Brute-force protection: too many failed logins → locked for a while
# ======================================================================
def _throttle_key(request, username: str) -> str:
    ip = request.META.get("REMOTE_ADDR", "?")
    return f"login-fail:{ip}:{username.lower()}"


def throttle_check(request, username: str) -> None:
    if (cache.get(_throttle_key(request, username)) or 0) >= settings.LOGIN_MAX_FAILURES:
        minutes = int(settings.LOGIN_LOCKOUT.total_seconds() // 60)
        raise TooManyRequests(f"Too many failed attempts. Try again in {minutes} minutes.")


def throttle_failed(request, username: str) -> None:
    key = _throttle_key(request, username)
    timeout = int(settings.LOGIN_LOCKOUT.total_seconds())
    if not cache.add(key, 1, timeout):
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout)


def throttle_reset(request, username: str) -> None:
    cache.delete(_throttle_key(request, username))


# ======================================================================
# 4. Endpoints
# ======================================================================
def user_json(user) -> dict | None:
    """The user as the frontend sees it. Passwords and key hashes are never sent."""
    if not user.is_authenticated:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "name": user.first_name or user.username,
        "is_admin": user.is_staff,
    }


def _session(user, key: str, row: ApiToken) -> dict:
    """What a successful login returns."""
    ttl = int(settings.TOKEN_TTL[row.role].total_seconds())
    return {
        "user": user_json(user),
        "token": key,
        "token_type": "Bearer",
        "role": row.role,
        "expires_at": row.expires_at.isoformat(),
        "expires_in": ttl,
    }


def _credentials(data: dict) -> tuple[str, str]:
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if not username or not password:
        raise BadRequest("Enter a username and a password.")
    return username, password


def _check_password(request, data: dict) -> User:
    username, password = _credentials(data)
    throttle_check(request, username)
    user = authenticate(request, username=username, password=password)
    if user is None:
        throttle_failed(request, username)
        raise Unauthorized("Wrong username or password.")
    throttle_reset(request, username)
    return user


# ------------------------------------------------------------------ user
@api_view(methods=("GET",))
def me(request, data):
    """Who owns the presented key (or null)."""
    auth = request.auth
    return {
        "user": user_json(request.user),
        "role": auth.role if auth else None,
        "expires_at": auth.expires_at.isoformat() if auth else None,
    }


@api_view()
def register(request, data):
    """Create a user (Django stores the password as a salted PBKDF2 hash) and log in."""
    username, password = _credentials(data)
    name = " ".join(str(data.get("name", "")).split())  # trim + collapse spaces
    if not name:
        raise BadRequest("Enter your name.")
    if len(name) > 60:
        raise BadRequest("Name is too long (max 60 characters).")
    if not (3 <= len(username) <= 30) or not username.replace("_", "").replace(".", "").isalnum():
        raise BadRequest("Username: 3–30 characters, letters, digits, '_' or '.'.")
    if User.objects.filter(username__iexact=username).exists():
        raise BadRequest("This username is already taken.")
    try:
        password_validation.validate_password(password, User(username=username))
    except ValidationError as e:
        raise BadRequest(" ".join(e.messages))

    with transaction.atomic():
        user = User.objects.create_user(username=username, password=password, first_name=name)
        key, row = issue_token(user, ApiToken.Role.USER, "browser")
    update_last_login(None, user)
    return _session(user, key, row)


@api_view()
def login_view(request, data):
    user = _check_password(request, data)
    key, row = issue_token(user, ApiToken.Role.USER, str(data.get("label", "browser")))
    update_last_login(None, user)
    return _session(user, key, row)


# ----------------------------------------------------------------- admin
@api_view()
def admin_login(request, data):
    """Step 1: password. Returns a one-time challenge that must be answered with the admin phrase."""
    user = _check_password(request, data)
    if not user.is_staff:
        raise Forbidden("This account is not an admin. Use the normal login.")
    challenge_id = secrets.token_urlsafe(24)
    question = "Admin check: type the admin phrase."
    AdminChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())  # old ones die
    AdminChallenge.objects.create(
        user=user,
        key_hash=hash_token(challenge_id),
        question=question,
        expires_at=timezone.now() + settings.ADMIN_CHALLENGE_TTL,
    )
    return {
        "challenge_id": challenge_id,
        "question": question,
        "expires_in": int(settings.ADMIN_CHALLENGE_TTL.total_seconds()),
        "attempts_left": settings.ADMIN_CHALLENGE_ATTEMPTS,
    }


@api_view()
def admin_verify(request, data):
    """Step 2: the answer to the challenge (the admin phrase). Returns an ADMIN key."""
    challenge_id = str(data.get("challenge_id", ""))
    answer = str(data.get("answer", ""))
    if not challenge_id or not answer.strip():
        raise BadRequest("Type the admin phrase.")
    try:
        ch = AdminChallenge.objects.select_related("user").get(key_hash=hash_token(challenge_id))
    except AdminChallenge.DoesNotExist:
        raise Unauthorized("This admin check is not valid. Start the admin login again.")
    now = timezone.now()
    if ch.used_at is not None or ch.expires_at <= now or ch.attempts >= settings.ADMIN_CHALLENGE_ATTEMPTS:
        raise Unauthorized("This admin check expired. Start the admin login again.")

    if not verify_admin_phrase(answer):
        ch.attempts += 1
        left = settings.ADMIN_CHALLENGE_ATTEMPTS - ch.attempts
        if left <= 0:
            ch.used_at = now
        ch.save(update_fields=["attempts", "used_at"])
        if left <= 0:
            raise Unauthorized("Wrong admin phrase. No attempts left — start the admin login again.")
        raise Unauthorized(f"Wrong admin phrase. {left} attempt{'s' if left != 1 else ''} left.")

    ch.used_at = now
    ch.save(update_fields=["used_at"])
    if not ch.user.is_staff:
        raise Forbidden("This account is not an admin.")
    key, row = issue_token(ch.user, ApiToken.Role.ADMIN, "admin browser")
    update_last_login(None, ch.user)
    return _session(ch.user, key, row)


# ------------------------------------------------------------ key handling
@api_view(login_required=True)
def refresh(request, data):
    """Swap the current key for a new one (same role, fresh expiry). The old key stops working."""
    current = request.auth
    with transaction.atomic():
        revoke(current)
        key, row = issue_token(request.user, current.role, current.label or "rotated")
    return _session(request.user, key, row)


@api_view()
def logout_view(request, data):
    """Revoke the presented key (if any)."""
    if request.auth is not None:
        revoke(request.auth)
    return {"user": None}


@api_view(methods=("GET",), login_required=True)
def my_tokens(request, data):
    rows = ApiToken.objects.filter(user=request.user, revoked_at__isnull=True, expires_at__gt=timezone.now())
    return {"tokens": [token_json(r, request.auth) for r in rows]}


@api_view(methods=("DELETE",), login_required=True)
def revoke_my_token(request, data, token_id: int):
    try:
        row = ApiToken.objects.get(pk=token_id, user=request.user)
    except ApiToken.DoesNotExist:
        raise NotFound("Key not found.")
    revoke(row)
    return {"revoked": token_id}
