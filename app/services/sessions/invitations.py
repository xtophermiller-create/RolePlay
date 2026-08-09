"""Приглашения в сессию.

Модель SessionInvitation выпилена из domain — API временно заглушен,
пока слой sessions не переведём на новый контракт (вход по коду).
"""

from __future__ import annotations

from app.services.result import Err, Result


def create_invitation(
    session_id: int, from_user_id: int, to_handle: str
) -> Result[dict]:
    return Err("not_implemented")


def list_incoming(user_id: int) -> list:
    return []


def list_outgoing(session_id: int, host_user_id: int) -> list:
    return []


def accept_invitation(invite_id: int, user_id: int) -> Result[dict]:
    return Err("not_implemented")


def decline_invitation(invite_id: int, user_id: int) -> Result[bool]:
    return Err("not_implemented")


def invitation_to_dict(invite) -> dict:
    return {}


def expire_pending() -> int:
    return 0
