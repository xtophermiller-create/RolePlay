"""Участники и роли в сессии (без presence/ping)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import RpSession, RpSessionParticipant
from app.domain.models.rp_session import (
    STATUS_ACTIVE,
    STATUS_LOBBY,
)
from app.domain.models.rp_session_participant import (
    ROLE_ACTOR1,
    ROLE_ACTOR2,
    ROLE_OBSERVER,
    SESSION_ROLES,
)
from app.extensions import db
from app.services.commit import try_commit
from app.services.result import Err, Ok, Result
from app.services.sessions import core as sessions_core

MAX_SESSION_PARTICIPANTS = 100
_ACTOR_ROLES = (ROLE_ACTOR1, ROLE_ACTOR2)

# Совместимость со старыми импортами.
SessionParticipant = RpSessionParticipant


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _open_session(session_id: int) -> RpSession | None:
    row = sessions_core.get_session(session_id)
    if not row or row.status not in (STATUS_LOBBY, STATUS_ACTIVE):
        return None
    return row


def add_participant(session_id: int, user_id: int) -> Result[RpSessionParticipant]:
    row = _open_session(session_id)
    if not row:
        return Err("session_closed")

    existing = sessions_core.get_participant(session_id, user_id)
    if existing:
        if not existing.role:
            existing.role = ROLE_OBSERVER
        if not try_commit():
            return Err("db_commit_failed")
        return Ok(existing)

    count = RpSessionParticipant.query.filter_by(session_id=session_id).count()
    if count >= MAX_SESSION_PARTICIPANTS:
        return Err("session_full")

    p = RpSessionParticipant(
        session_id=session_id,
        user_id=user_id,
        role=ROLE_OBSERVER,
    )
    db.session.add(p)
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(p)


def leave_session(session_id: int, user_id: int) -> Result[bool]:
    row = sessions_core.get_session(session_id)
    if not row:
        return Err("not_found")
    if row.status == STATUS_ACTIVE:
        return Err("cannot_leave_active")
    if row.host_user_id == user_id:
        return Err("host_cannot_leave")
    p = sessions_core.get_participant(session_id, user_id)
    if not p:
        return Err("not_participant")
    db.session.delete(p)
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(True)


def choose_role(
    session_id: int, user_id: int, role: str | None
) -> Result[RpSessionParticipant]:
    row = _open_session(session_id)
    if not row:
        return Err("session_closed")
    if row.status != STATUS_LOBBY:
        return Err("invalid_status")

    p = sessions_core.get_participant(session_id, user_id)
    if not p:
        return Err("not_participant")

    if role is not None:
        role = (role or "").strip()
        if role not in SESSION_ROLES:
            return Err("invalid_role")
        if role in _ACTOR_ROLES:
            taken = (
                RpSessionParticipant.query.filter(
                    RpSessionParticipant.session_id == session_id,
                    RpSessionParticipant.role == role,
                    RpSessionParticipant.user_id != user_id,
                ).first()
            )
            if taken:
                return Err("role_taken")
        p.role = role
    else:
        p.role = ROLE_OBSERVER

    if not try_commit():
        return Err("db_commit_failed")
    return Ok(p)


def roles_ready(session_id: int) -> bool:
    """Оба актёрских слота заняты."""
    counts = {ROLE_ACTOR1: 0, ROLE_ACTOR2: 0}
    for p in sessions_core.list_participants(session_id):
        if p.role in counts:
            counts[p.role] += 1
    return counts[ROLE_ACTOR1] == 1 and counts[ROLE_ACTOR2] == 1


def actors_ready(session_id: int) -> bool:
    """Совместимость со старым API: теперь = roles_ready (is_ready убран)."""
    return roles_ready(session_id)


def set_ready(session_id: int, user_id: int, ready: bool = True) -> Result[bool]:
    """Заглушка: ready-флагов больше нет."""
    del session_id, user_id, ready
    return Err("not_implemented")


def mark_away(session_id: int, user_id: int) -> Result[bool]:
    """Заглушка: presence убран."""
    del session_id, user_id
    return Ok(True)


def ping(session_id: int, user_id: int) -> Result[dict]:
    """Заглушка: отдаём текущее состояние сессии без heartbeat."""
    row = sessions_core.get_session(session_id)
    if not row:
        return Err("not_found")
    p = sessions_core.get_participant(session_id, user_id)
    if not p and row.host_user_id != user_id:
        return Err("not_participant")
    return Ok(sessions_core.session_to_dict(row))


def prune_stale_participants(session_id: int) -> dict:
    del session_id
    return {"removed": 0, "cancelled": False}


def prune_all_stale_sessions() -> int:
    return 0
