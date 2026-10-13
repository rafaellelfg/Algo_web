"""Small helpers shared by all JSON API views."""
import json
from functools import wraps

from django.http import HttpRequest, JsonResponse

from tree.bst import TreeFormatError


class BadRequest(Exception):
    """Raise inside a view to answer with HTTP 400 and {"error": message}."""


class Unauthorized(Exception):
    """Raise inside a view to answer with HTTP 401."""


class NotFound(Exception):
    """Raise inside a view to answer with HTTP 404."""


def parse_json(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        raise BadRequest("Request body must be JSON.")
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object.")
    return data


def api_view(methods=("POST",), login_required=False):
    """
    Decorator for JSON endpoints.
    The view receives (request, data, **kwargs) and returns a dict.
    CSRF protection stays on: the frontend sends the X-CSRFToken header.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request: HttpRequest, **kwargs) -> JsonResponse:
            if request.method not in methods:
                return JsonResponse({"error": f"Method {request.method} not allowed."}, status=405)
            try:
                if login_required and not request.user.is_authenticated:
                    raise Unauthorized("Please log in first.")
                result = func(request, parse_json(request), **kwargs)
                return JsonResponse(result, status=200)
            except (BadRequest, TreeFormatError) as e:
                return JsonResponse({"error": str(e)}, status=400)
            except Unauthorized as e:
                return JsonResponse({"error": str(e)}, status=401)
            except NotFound as e:
                return JsonResponse({"error": str(e)}, status=404)

        return wrapper

    return decorator
