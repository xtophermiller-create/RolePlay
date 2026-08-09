"""Завершение боя и история сессий для участников."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.models import RpSession, RpSessionParticipant
from app.domain.models.rp_session import STATUS_ACTIVE, STATUS_FINISHED
from app.domain.models.rp_session_participant import ROLE_OBSERVER
from app.services.commit import try_commit
from app.services.result import Err, Ok, Result
from app.services.sessions import core as sessions_core
from app.services.users import display_name, get_user


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def complete_session(
    session_id: int,
    user_id: int,
    *,
    values: dict[str, Any] | None = None,
    roles: dict[str, Any] | None = None,
) -> Result[RpSession]:
    """Завершить бой. values/roles игнорируются (оценки удалены)."""
    del values, roles
    row = sessions_core.get_session(session_id)
    if not row:
        return Err("not_found")
    if row.status != STATUS_ACTIVE:
        return Err("invalid_status")

    participant = sessions_core.get_participant(session_id, user_id)
    is_observer = bool(participant and participant.role == ROLE_OBSERVER)
    is_host = row.host_user_id == user_id
    if not is_observer and not is_host:
        return Err("forbidden")

    row.status = STATUS_FINISHED
    row.finished_at = _utcnow()

    if not try_commit():
        return Err("db_commit_failed")
    return Ok(row)


def result_payload(session: RpSession) -> dict[str, Any] | None:
    del session
    return None


def history_entry(session: RpSession) -> dict[str, Any]:
    participants = [
        sessions_core.participant_to_dict(p)
        for p in sessions_core.list_participants(session.session_id)
    ]
    host = get_user(session.host_user_id)
    return {
        "session_id": session.session_id,
        "code": session.code,
        "status": session.status,
        "scenario_title": session.scenario_title,
        "host_user_id": session.host_user_id,
        "host_name": display_name(host) if host else None,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "finished_at": session.finished_at.isoformat() if session.finished_at else None,
        "participants": participants,
    }


def list_history(user_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = (
        RpSession.query.join(
            RpSessionParticipant,
            RpSessionParticipant.session_id == RpSession.session_id,
        )
        .filter(
            RpSessionParticipant.user_id == user_id,
            RpSession.status == STATUS_FINISHED,
        )
        .order_by(RpSession.finished_at.desc())
        .limit(max(1, min(int(limit or 50), 200)))
        .all()
    )
    return [history_entry(row) for row in rows]


def get_history_item(session_id: int, user_id: int) -> Result[dict[str, Any]]:
    row = sessions_core.get_session(session_id)
    if not row or row.status != STATUS_FINISHED:
        return Err("not_found")
    if row.host_user_id != user_id:
        participant = sessions_core.get_participant(session_id, user_id)
        if not participant:
            return Err("forbidden")
    return Ok(history_entry(row))
