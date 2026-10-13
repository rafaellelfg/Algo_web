"""Registration / login / logout with Django's built-in users and session cookies."""
from django.contrib.auth import authenticate, login, logout, password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie

from config.api import BadRequest, Unauthorized, api_view


def _user_json(user) -> dict | None:
    """The user as the frontend sees it. The password (hash) is never sent."""
    if not user.is_authenticated:
        return None
    return {"id": user.id, "username": user.username, "name": user.first_name or user.username}


def _credentials(data: dict) -> tuple[str, str]:
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if not username or not password:
        raise BadRequest("Enter a username and a password.")
    return username, password


@ensure_csrf_cookie
@api_view(methods=("GET",))
def me(request, data):
    """Who is logged in. Also sets the csrftoken cookie for the frontend."""
    return {"user": _user_json(request.user)}


@api_view()
def register(request, data):
    """Create a user. Django stores the password as a salted hash, never as plain text."""
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

    user = User.objects.create_user(username=username, password=password, first_name=name)
    login(request, user)
    return {"user": _user_json(user)}


@api_view()
def login_view(request, data):
    username, password = _credentials(data)
    user = authenticate(request, username=username, password=password)
    if user is None:
        raise Unauthorized("Wrong username or password.")
    login(request, user)
    return {"user": _user_json(user)}


@api_view()
def logout_view(request, data):
    logout(request)
    return {"user": None}
