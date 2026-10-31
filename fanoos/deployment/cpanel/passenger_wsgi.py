"""cPanel / Phusion Passenger entry point for Fanoos.

In cPanel → "Setup Python App":
    Application startup file:  passenger_wsgi.py
    Application Entry point:   application

Passenger speaks WSGI; Fanoos is a FastAPI (ASGI) app, so ``a2wsgi`` adapts it.
API keys and settings come from the environment variables set in the Python App
page (or from a ``.env`` file in this folder, which must never be web-accessible).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
os.environ.setdefault("FANOOS_ROOT", HERE)

from a2wsgi import ASGIMiddleware  # noqa: E402

from fanoos.server import app as asgi_app  # noqa: E402

application = ASGIMiddleware(asgi_app)
