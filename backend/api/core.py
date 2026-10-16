"""Shared helpers for every JSON endpoint: errors, JSON parsing and the @api_view decorator.

Authentication for /api/ is ONLY the header  `Authorization: Bearer <key>`.
Session cookies are ignored here on purpose: because the browser never sends
the key automatically, the API needs no CSRF protection.
"""
import json
from functools import wraps

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from algorithms.build import GraphError, TreeFormatError


class ApiError(Exception):
    status = 400
    code = "bad_request"


class BadRequest(ApiError):
    """HTTP 400 and {"error": message}."""


class Unauthorized(ApiError):
    """HTTP 401: not logged in / bad credentials."""

    status = 401
    code = "unauthorized"


class Forbidden(ApiError):
    """HTTP 403: logged in, but not allowed (e.g. not an admin)."""

    status = 403
    code = "forbidden"


class NotFound(ApiError):
    status = 404
    code = "not_found"


class TooManyRequests(ApiError):
    status = 429
    code = "too_many_requests"


def parse_json(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise BadRequest("Request body must be JSON.")
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object.")
    return data


def _error(status: int, message: str, code: str) -> JsonResponse:
    response = JsonResponse({"error": message, "code": code}, status=status)
    if status == 401:
        response["WWW-Authenticate"] = 'Bearer realm="api"'
    return response


def api_view(methods=("POST",), login_required=False, admin_required=False):
   

    def decorator(func):
        @csrf_exempt
        @wraps(func)
        def wrapper(request: HttpRequest, **kwargs) -> JsonResponse:
            from .login import TokenError, check_token, parse_authorization

            if request.method not in methods:
                return _error(405, f"Method {request.method} not allowed.", "method_not_allowed")

            request.user = AnonymousUser()  # never trust the session cookie on the API
            request.auth = None
            try:
                key = parse_authorization(request.headers.get("Authorization"))
                if key is not None:
                    request.auth = check_token(key)
                    request.user = request.auth.user
            except TokenError as e:
                return _error(401, str(e), "token_invalid")

            try:
                if (login_required or admin_required) and not request.user.is_authenticated:
                    raise Unauthorized("Please log in first.")
                if admin_required and (request.auth.role != "admin" or not request.user.is_staff):
                    raise Forbidden("Admins only. Log in with the admin login (password + admin phrase).")
                result = func(request, parse_json(request), **kwargs)
                return JsonResponse(result, status=200)
            except TreeFormatError as e:
                return _error(400, str(e), "bad_tree")
            except GraphError as e:
                return _error(400, str(e), "bad_graph")
            except ApiError as e:
                return _error(e.status, str(e), e.code)

        return wrapper

    return decorator
