import os
import sys

# Ensure repository root and platform directory are on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLATFORM_DIR = os.path.join(REPO_ROOT, "platform")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if PLATFORM_DIR not in sys.path:
    sys.path.insert(0, PLATFORM_DIR)

try:
    from backend.main import app
except ImportError:
    from platform.backend.main import app

# Export app for Vercel Python Serverless Runtime
__all__ = ["app"]
