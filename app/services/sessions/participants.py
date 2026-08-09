"""Участники и роли в сессии."""

from __future__ import annotations

from app.domain.models import RpSession, RpSessionParticipant
from app.domain.models.rp_session import (
    BRIEF_STATUSES,
    LIVE_STATUSES,
    STATUS_LOBBY,
    STATUS_READY,
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


def _open_session(session_id: int) -> RpSession | None:
    row = sessions_core.get_session(session_id)
    if not row or row.status not in (STATUS_LOBBY, *LIVE_STATUSES):
        return None
    return row


def add_participant(session_id: int, user_id: int) -> Result[RpSessionParticipant]:
    row = _open_session(session_id)
    if not row:
        return Err("session_closed")
    if row.status != STATUS_LOBBY:
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
        is_ready=False,
    )
    db.session.add(p)
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(p)


def leave_session(session_id: int, user_id: int) -> Result[bool]:
    row = sessions_core.get_session(session_id)
    if not row:
        return Err("not_found")
    if row.status in LIVE_STATUSES:
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

    p.is_ready = False
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(p)


def mark_ready(session_id: int, user_id: int) -> Result[RpSession]:
    """Актёр жмёт «Готов». Когда оба готовы — сессия started → ready."""
    row = sessions_core.get_session(session_id)
    if not row:
        return Err("not_found")
    if row.status not in BRIEF_STATUSES:
        if row.status == STATUS_READY:
            return Ok(row)
        return Err("invalid_status")

    p = sessions_core.get_participant(session_id, user_id)
    if not p:
        return Err("not_participant")
    if p.role not in _ACTOR_ROLES:
        return Err("forbidden")

    p.is_ready = True

    ready = {ROLE_ACTOR1: False, ROLE_ACTOR2: False}
    for other in sessions_core.list_participants(session_id):
        if other.role in ready and other.is_ready:
            ready[other.role] = True
    if ready[ROLE_ACTOR1] and ready[ROLE_ACTOR2]:
        row.status = STATUS_READY
        row.ready_at = sessions_core._utcnow()

    if not try_commit():
        return Err("db_commit_failed")
    return Ok(row)


def roles_ready(session_id: int) -> bool:
    """Оба актёрских слота заняты."""
    counts = {ROLE_ACTOR1: 0, ROLE_ACTOR2: 0}
    for p in sessions_core.list_participants(session_id):
        if p.role in counts:
            counts[p.role] += 1
    return counts[ROLE_ACTOR1] == 1 and counts[ROLE_ACTOR2] == 1


def free_roles(session_id: int) -> list[str]:
    """Свободные роли для UI лобби (observer всегда доступен)."""
    taken = {
        p.role
        for p in sessions_core.list_participants(session_id)
        if p.role in _ACTOR_ROLES
    }
    free = [role for role in _ACTOR_ROLES if role not in taken]
    free.append(ROLE_OBSERVER)
    return free


def heartbeat(session_id: int, user_id: int) -> Result[RpSession]:
    """Обновление состояния лобби/боя (presence убран — просто проверка доступа)."""
    row = sessions_core.get_session(session_id)
    if not row:
        return Err("not_found")
    p = sessions_core.get_participant(session_id, user_id)
    if not p and row.host_user_id != user_id:
        return Err("not_participant")
    return Ok(row)
