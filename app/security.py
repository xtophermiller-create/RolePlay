"""Host allowlist, JSON size limit, Turnstile verify, security response headers.

CSRF живёт в app.extensions (Flask-WTF), не здесь.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from flask import abort, current_app, request


def verify_turnstile(token: str, remote_ip: str | None) -> bool:
    secret = current_app.config["TURNSTILE_SECRET_KEY"]
    required = current_app.config["TURNSTILE_REQUIRED"]
    if not secret:
        return not required
    if not token:
        return False
    payload = urllib.parse.urlencode(
        {"secret": secret, "response": token, "remoteip": remote_ip or ""}
    ).encode()
    try:
        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=payload,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.load(response)
        return result.get("success") is True
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def install_request_security(app) -> None:
    @app.before_request
    def enforce_request_rules():
        trusted = app.config["TRUSTED_HOSTS"]
        if trusted:
            host = request.host.split(":", 1)[0].lower()
            if host not in {item.lower() for item in trusted}:
                abort(400)
        if request.is_json and request.content_length:
            if request.content_length > app.config["MAX_JSON_BYTES"]:
                abort(413)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
            "connect-src 'self' https://challenges.cloudflare.com; frame-src "
            "https://challenges.cloudflare.com; frame-ancestors 'none'; base-uri 'self'; "
            "form-action 'self'",
        )
        if app.config["HSTS_ENABLED"] and request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
