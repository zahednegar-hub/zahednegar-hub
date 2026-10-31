"""The cPanel/Passenger WSGI entry point loads the app and serves requests (no network)."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

ENTRY = Path(__file__).resolve().parent.parent / "deployment" / "cpanel" / "passenger_wsgi.py"


def call(
    application, path: str, method: str = "GET", body: bytes = b"", content_type: str = ""
) -> tuple[str, dict, bytes]:
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "fanoos.example",
        "SERVER_PORT": "443",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "REMOTE_ADDR": "203.0.113.5",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "https",
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": io.StringIO(),
        "wsgi.multithread": True,
        "wsgi.multiprocess": True,
        "wsgi.run_once": False,
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
    }
    result: dict = {}

    def start_response(status, headers, exc_info=None):
        result["status"], result["headers"] = status, {k.lower(): v for k, v in headers}

    chunks = b"".join(application(environ, start_response))
    return result["status"], result["headers"], chunks


def load_entry():
    spec = importlib.util.spec_from_file_location("passenger_wsgi_under_test", ENTRY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.application


def test_passenger_entry_serves_health_page_and_assets() -> None:
    application = load_entry()
    status, headers, body = call(application, "/health")
    assert status.startswith("200") and json.loads(body)["status"] == "ok"
    assert "strict-transport-security" in headers  # https scheme from Passenger
    status, headers, body = call(application, "/")
    assert status.startswith("200") and b'id="lantern-stage"' in body and "content-security-policy" in headers
    status, headers, _ = call(application, "/static/vendor/three/three.module.min.js")
    assert status.startswith("200") and "javascript" in headers["content-type"]


def test_passenger_entry_reports_missing_key() -> None:
    application = load_entry()
    status, _, body = call(application, "/api/review", "POST", b'{"url": "https://example.com"}', "application/json")
    assert status.startswith("503") and json.loads(body)["type"] == "MissingAPIKeyError"
