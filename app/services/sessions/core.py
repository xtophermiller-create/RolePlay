"""Создание / чтение / статус ролевых сессий."""

from __future__ import annotations

import json
import secrets
import string
from datetime import datetime, timezone
from typing import Any

from app.domain.models import RpSession, RpSessionParticipant, Scenario, User
from app.domain.models.rp_session import (
    SESSION_STATUSES,
    STATUS_ACTIVE,
    STATUS_CANCELLED,
    STATUS_FINISHED,
    STATUS_LOBBY,
)
from app.domain.models.rp_session_participant import ROLE_OBSERVER
from app.domain.scenario.document import document_title
from app.extensions import db
from app.services.commit import try_commit
from app.services.result import Err, Ok, Result
from app.services.scenarios import files as scenario_files
from app.services.users import display_name, get_user

_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LEN = 8

# Временный алиас для старых импортов внутри пакета.
SessionParticipant = RpSessionParticipant


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_code() -> str:
    for _ in range(32):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))
        if not RpSession.query.filter_by(code=code).first():
            return code
    raise RuntimeError("session_code_exhausted")


def get_session(session_id: int) -> RpSession | None:
    return RpSession.query.filter_by(session_id=session_id).first()


def get_session_by_code(code: str) -> RpSession | None:
    code = (code or "").strip().upper()
    if not code:
        return None
    return RpSession.query.filter_by(code=code).first()


def get_participant(session_id: int, user_id: int) -> RpSessionParticipant | None:
    return RpSessionParticipant.query.filter_by(
        session_id=session_id, user_id=user_id
    ).first()


def list_participants(session_id: int) -> list[RpSessionParticipant]:
    return (
        RpSessionParticipant.query.filter_by(session_id=session_id)
        .order_by(RpSessionParticipant.participant_id.asc())
        .all()
    )


def create_session(host_user_id: int, scenario_id: int) -> Result[RpSession]:
    """Хост создаёт сессию по своему сценарию → lobby + сам как observer."""
    host = User.query.filter_by(user_id=host_user_id).first()
    if not host:
        return Err("user_not_found")
    if getattr(host, "is_guest", False):
        return Err("guests_forbidden")

    scenario = Scenario.query.filter_by(
        scenario_id=scenario_id, owner_user_id=host_user_id
    ).first()
    if not scenario:
        return Err("scenario_not_found")

    try:
        document = scenario_files.read_document(scenario.file_name)
    except (OSError, ValueError, json.JSONDecodeError):
        return Err("scenario_file_missing")

    title = document_title(document) or scenario.title or "Без названия"
    try:
        snapshot = json.dumps(document, ensure_ascii=False)
    except (TypeError, ValueError):
        return Err("scenario_snapshot_failed")

    row = RpSession(
        code=_new_code(),
        host_user_id=host_user_id,
        scenario_id=scenario_id,
        scenario_title=title[:200],
        scenario_snapshot=snapshot,
        status=STATUS_LOBBY,
    )
    db.session.add(row)
    db.session.flush()
    db.session.add(
        RpSessionParticipant(
            session_id=row.session_id,
            user_id=host_user_id,
            role=ROLE_OBSERVER,
        )
    )
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(row)


def start_session(session_id: int, host_user_id: int) -> Result[RpSession]:
    from app.services.sessions import participants as participants_service

    row = get_session(session_id)
    if not row or row.host_user_id != host_user_id:
        return Err("not_found")
    if row.status != STATUS_LOBBY:
        return Err("invalid_status")
    if not participants_service.roles_ready(session_id):
        return Err("roles_not_ready")
    now = _utcnow()
    row.status = STATUS_ACTIVE
    row.started_at = now
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(row)


def finish_session(session_id: int, host_user_id: int) -> Result[RpSession]:
    row = get_session(session_id)
    if not row or row.host_user_id != host_user_id:
        return Err("not_found")
    if row.status not in (STATUS_LOBBY, STATUS_ACTIVE):
        return Err("invalid_status")
    row.status = STATUS_FINISHED
    row.finished_at = _utcnow()
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(row)


def cancel_session(session_id: int, host_user_id: int) -> Result[RpSession]:
    row = get_session(session_id)
    if not row or row.host_user_id != host_user_id:
        return Err("not_found")
    if row.status in (STATUS_FINISHED, STATUS_CANCELLED):
        return Err("invalid_status")
    row.status = STATUS_CANCELLED
    row.finished_at = _utcnow()
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(row)


def scenario_document(session: RpSession) -> dict[str, Any]:
    return json.loads(session.scenario_snapshot)


def play_payload(session_id: int, user_id: int) -> Result[dict[str, Any]]:
    """Данные для экрана «боя»."""
    row = get_session(session_id)
    if not row:
        return Err("not_found")
    participant = get_participant(session_id, user_id)
    if not participant and row.host_user_id != user_id:
        return Err("not_participant")
    if row.status not in (STATUS_ACTIVE, STATUS_FINISHED):
        return Err("not_started")

    my_role = participant.role if participant else None
    try:
        document = scenario_document(row)
    except (TypeError, ValueError, json.JSONDecodeError):
        return Err("scenario_snapshot_failed")

    return Ok(
        {
            "session": session_to_dict(row),
            "my_role": my_role,
            "document": document,
            "ui_hint": {
                "actor1": ["roles.actor1"],
                "actor2": ["roles.actor2"],
                "observer": ["roles.actor1", "roles.actor2"],
            },
        }
    )


def session_to_dict(session: RpSession, *, include_participants: bool = True) -> dict:
    data = {
        "session_id": session.session_id,
        "code": session.code,
        "host_user_id": session.host_user_id,
        "scenario_id": session.scenario_id,
        "scenario_title": session.scenario_title,
        "status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ready_at": session.ready_at.isoformat() if session.ready_at else None,
        "finished_at": session.finished_at.isoformat() if session.finished_at else None,
    }
    if include_participants:
        data["participants"] = [
            participant_to_dict(p) for p in list_participants(session.session_id)
        ]
    return data


def participant_to_dict(p: RpSessionParticipant) -> dict:
    user = get_user(p.user_id)
    return {
        "participant_id": p.participant_id,
        "user_id": p.user_id,
        "role": p.role,
        "login": user.login if user else None,
        "nickname": display_name(user) if user else None,
    }


def assert_status(status: str) -> bool:
    return status in SESSION_STATUSES
