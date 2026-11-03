from __future__ import annotations

from urllib.parse import urlsplit
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask, Response

# JS только своими файлами (никогда 'unsafe-inline'), CSS запрещён
SECURITY_HEADERS = {
    'Content-Security-Policy': (
        "default-src 'self'; script-src 'self'; style-src 'none'; img-src 'self'; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    ),
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'same-origin',
}


def is_safe_path(target: str | None) -> bool:
    ''' Относительный путь своего сайта, защита от открытого редиректа '''
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target:
        return False
    parts = urlsplit(target)
    return not parts.scheme and not parts.netloc


def _set_security_headers(response: Response) -> Response:
    response.headers.update(SECURITY_HEADERS)
    return response


def register_security(app: Flask) -> None:
    app.after_request(_set_security_headers)
