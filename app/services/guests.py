"""Эфемерные гости: создание, TTL, удаление."""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta, timezone

from flask import current_app

from app.domain.models import RpSession, RpSessionParticipant, Scenario, User
from app.extensions import db
from app.services.auth import hash_password, make_password
from app.services.commit import try_commit
from app.services.result import Err, Ok, Result

_DEFAULT_TTL_SECONDS = 24 * 60 * 60
_PURGE_INTERVAL_SECONDS = 300
_last_purge_monotonic: float = 0.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ttl_seconds() -> int:
    try:
        return max(60, int(current_app.config.get("GUEST_TTL_SECONDS", _DEFAULT_TTL_SECONDS)))
    except RuntimeError:
        return _DEFAULT_TTL_SECONDS


def guest_created_at(user: User) -> datetime | None:
    value = user.created_at
    if value is None:
        return None
    if getattr(value, "tzinfo", None) is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def is_expired(user: User, *, now: datetime | None = None) -> bool:
    if not getattr(user, "is_guest", False):
        return False
    created = guest_created_at(user)
    if created is None:
        return True
    now = now or _utcnow()
    return created < now - timedelta(seconds=ttl_seconds())


def expires_at(user: User) -> datetime | None:
    created = guest_created_at(user)
    if created is None:
        return None
    return created + timedelta(seconds=ttl_seconds())


def _unique_guest_login() -> str:
    for _ in range(12):
        login = f"guest_{secrets.token_hex(12)}"
        if not User.query.filter_by(login=login).first():
            return login
    return f"guest_{secrets.token_hex(16)}"


def _unique_guest_nickname() -> str:
    for _ in range(24):
        nick = f"Гость-{secrets.token_hex(2).upper()}"
        if (
            not User.query.filter_by(nickname=nick).first()
            and not User.query.filter_by(login=nick).first()
        ):
            return nick
    return f"Гость-{secrets.token_hex(4).upper()}"


def create_guest() -> Result[User]:
    """Создать эфемерного пользователя-гостя."""
    login = _unique_guest_login()
    nickname = _unique_guest_nickname()
    user = User(
        login=login,
        password=hash_password(make_password(32)),
        nickname=nickname,
        is_guest=True,
        is_admin=False,
    )
    db.session.add(user)
    if not try_commit():
        return Err("guest_create_failed")
    return Ok(user)


def delete_guest(user: User | int) -> bool:
    """Удалить гостя и связанные строки (участники / сессии)."""
    if isinstance(user, int):
        row = User.query.filter_by(user_id=user, is_guest=True).first()
    else:
        row = user if getattr(user, "is_guest", False) else None
    if not row:
        return False

    uid = row.user_id
    RpSessionParticipant.query.filter_by(user_id=uid).delete(synchronize_session=False)

    # Гость не должен быть хостом; на всякий случай убираем сессии
    for hosted in RpSession.query.filter_by(host_user_id=uid).all():
        db.session.delete(hosted)

    for scenario in Scenario.query.filter_by(owner_user_id=uid).all():
        db.session.delete(scenario)

    db.session.delete(row)
    return bool(try_commit())


def purge_expired_guests(*, limit: int = 200) -> int:
    """Удалить гостей старше TTL. Возвращает число удалённых."""
    cutoff = _utcnow() - timedelta(seconds=ttl_seconds())
    rows = (
        User.query.filter(User.is_guest.is_(True), User.created_at < cutoff)
        .order_by(User.created_at.asc())
        .limit(max(1, min(int(limit or 200), 500)))
        .all()
    )
    deleted = 0
    for row in rows:
        if delete_guest(row):
            deleted += 1
    return deleted


def maybe_purge_expired() -> int:
    """Периодическая очистка (не чаще раз в 5 минут на процесс)."""
    global _last_purge_monotonic
    now = time.monotonic()
    if now - _last_purge_monotonic < _PURGE_INTERVAL_SECONDS:
        return 0
    _last_purge_monotonic = now
    return purge_expired_guests()
