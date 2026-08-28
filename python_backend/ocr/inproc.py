"""In-process OCR client — no HTTP, no port 5001."""
from __future__ import annotations

import threading
from io import BytesIO

_lock = threading.Lock()


def _flask_app():
    from ocr.engine import app as flask_app
    return flask_app


def post_ocr(file_bytes: bytes, filename: str, document_type: str | None = None) -> tuple[int, dict]:
    data = {"file": (BytesIO(file_bytes), filename or "upload.jpg")}
    if document_type:
        data["document_type"] = document_type
    with _lock:
        client = _flask_app().test_client()
        rv = client.post("/api/v1/ocr", data=data)
        body = rv.get_json(silent=True)
        if body is None:
            body = {"error": (rv.data or b"")[:300].decode("utf-8", errors="ignore")}
        return rv.status_code, body


def post_live_verify(payload: dict) -> tuple[int, dict]:
    with _lock:
        client = _flask_app().test_client()
        rv = client.post("/api/v1/live_verify", json=payload)
        body = rv.get_json(silent=True)
        if body is None:
            body = {"error": (rv.data or b"")[:300].decode("utf-8", errors="ignore")}
        return rv.status_code, body
