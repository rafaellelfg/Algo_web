from django.conf import settings
from django.http import HttpResponse


class SimpleCorsMiddleware:
    """Minimal CORS for /api/ without third-party packages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        allowed = origin in getattr(settings, "CORS_ALLOWED_ORIGINS", [])

        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if allowed and request.path.startswith("/api/"):
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
            response["Access-Control-Allow-Credentials"] = "true"
        return response
