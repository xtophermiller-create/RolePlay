"""Persistent auth throttling using the application's SQL database."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import or_

from app.domain.models import AuthAttempt
from app.extensions import db


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _key(kind: str, value: str) -> str:
    normalized = f"{kind}\0{value.strip().casefold()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _bucket(action: str, digest: str, create: bool = False):
    row = AuthAttempt.query.filter_by(action=action, identity_hash=digest).first()
    if row is None and create:
        row = AuthAttempt(
            action=action, identity_hash=digest, failures=0, window_started_at=_now()
        )
        db.session.add(row)
    return row


def _digests(ip: str, login: str) -> tuple[str, str]:
    return _key("ip", ip), _key("login", login)


def status(action: str, ip: str, login: str) -> tuple[bool, int]:
    now = _now()
    rows = [_bucket(action, digest) for digest in _digests(ip, login)]
    failures = max((row.failures for row in rows if row), default=0)
    blocked = any(row.blocked_until and row.blocked_until > now for row in rows if row)
    return blocked, failures


def record_failure(action: str, ip: str, login: str) -> int:
    now = _now()
    window = timedelta(seconds=current_app.config["AUTH_WINDOW_SECONDS"])
    rows = [_bucket(action, digest, create=True) for digest in _digests(ip, login)]
    for row in rows:
        if row.window_started_at < now - window:
            row.failures = 0
            row.window_started_at = now
            row.blocked_until = None
        row.failures += 1
        if row.failures >= current_app.config["AUTH_MAX_FAILURES"]:
            exponent = min(row.failures - current_app.config["AUTH_MAX_FAILURES"], 4)
            seconds = current_app.config["AUTH_BLOCK_SECONDS"] * (2**exponent)
            row.blocked_until = now + timedelta(seconds=seconds)
        row.updated_at = now
    db.session.commit()
    return max(row.failures for row in rows)


def clear(action: str, ip: str, login: str) -> None:
    rows = [_bucket(action, digest) for digest in _digests(ip, login)]
    for row in rows:
        if row:
            db.session.delete(row)
    db.session.commit()


def cleanup() -> int:
    cutoff = _now() - timedelta(days=2)
    count = AuthAttempt.query.filter(
        AuthAttempt.updated_at < cutoff,
        or_(AuthAttempt.blocked_until.is_(None), AuthAttempt.blocked_until < _now()),
    ).delete(synchronize_session=False)
    db.session.commit()
    return count
