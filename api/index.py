import os
import sys
from urllib.parse import parse_qs, urlencode

# Ensure repository root and platform directory are on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLATFORM_DIR = os.path.join(REPO_ROOT, "platform")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if PLATFORM_DIR not in sys.path:
    sys.path.insert(0, PLATFORM_DIR)

from backend.main import app as fastapi_app

class VercelRouteMiddleware:
    """Restores the true REST API route and parameters when Vercel rewrites to api/index.py."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            qs = scope.get("query_string", b"").decode("utf-8")
            if "_route" in qs:
                params = parse_qs(qs)
                if "_route" in params:
                    route = params.pop("_route")[0]
                    clean_route = "/" + route.lstrip("/")
                    if not clean_route.startswith("/api"):
                        clean_route = "/api" + clean_route
                    scope["path"] = clean_route
                    scope["raw_path"] = clean_route.encode("utf-8")
                    scope["query_string"] = urlencode(params, doseq=True).encode("utf-8")
        await self.app(scope, receive, send)

# Wrapped ASGI application
app = VercelRouteMiddleware(fastapi_app)
handler = app
application = app

__all__ = ["app", "handler", "application"]
