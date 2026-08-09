"""Minimal production logging without request secrets."""

from __future__ import annotations

import logging
import re
import sys
import time
from urllib.parse import urlsplit

from flask import g, request

_SENSITIVE = re.compile(
    r"(?i)\b(password|passwd|secret|token|authorization|cookie|session)"
    r"(\s*[:=]\s*)([^\s,;&]+)"
)
_URL_CREDENTIAL = re.compile(r"(?i)(mysql(?:\+pymysql)?://[^:\s]+:)[^@\s]+(@)")


def _redact(value: str) -> str:
    value = _SENSITIVE.sub(r"\1\2[REDACTED]", value)
    return _URL_CREDENTIAL.sub(r"\1[REDACTED]\2", value)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(record.getMessage())
        record.args = ()
        return True


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _redact(super().format(record))


def configure_logging(app) -> None:
    if app.config["APP_ENV"] != "production":
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        RedactingFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    if not any(getattr(item, "_roleplay_handler", False) for item in root.handlers):
        handler._roleplay_handler = True
        root.addHandler(handler)
    root.setLevel(logging.INFO)

    @app.before_request
    def _start_request_timer():
        g.request_started_at = time.monotonic()

    @app.after_request
    def _log_request(response):
        elapsed_ms = int(
            (time.monotonic() - getattr(g, "request_started_at", time.monotonic())) * 1000
        )
        # urlsplit ensures query strings and fragments never reach access logs.
        path = urlsplit(request.url).path
        app.logger.info(
            "request method=%s path=%s status=%s duration_ms=%s remote=%s",
            request.method,
            path,
            response.status_code,
            elapsed_ms,
            request.remote_addr or "-",
        )
        return response
