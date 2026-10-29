from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, validate_fields
from ..app import db
from ..domain import User


def get_profile(
        *,
        user_id: int | None = None,
) -> Result[tuple[str | None, str | None]]:
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)

    try:
        with db.session.begin():
            row = db.session.execute(
                select(User.nickname, User.avatar).where(User.id == user_id)
            ).one_or_none()

        if row is None:
            return Err(meta="profile not found", severity=Severity.INFO)

        return Ok(value=(row.nickname, row.avatar))
    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)


@dataclass
class PatchProfile:
    nickname: str | None = None
    avatar: str | None = None

def update_profile(
        *,
        user_id: int | None = None,
        patch: PatchProfile | None = None,
) -> Result:
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)
    if not patch:
        return Err(meta="patch is missing", severity=Severity.ERROR)
    if not isinstance(patch, PatchProfile):
        return Err(meta="patch must be a PatchProfile instance", severity=Severity.ERROR)

    nickname, avatar = patch.nickname, patch.avatar

    res = validate_fields(nickname=nickname, avatar=avatar)
    nickname = res['nickname']['checked']
    avatar = res['avatar']['checked']
    if not nickname or not avatar:
        return Err(meta='Incorrect fields', severity=Severity.ERROR)
    nickname = res['nickname']['normal'].value
    avatar = res['avatar']['normal'].value

    if all(value is None for value in (nickname, avatar)):
        return Ok(meta="No fields to update")

    values = {}
    if nickname is not None:
        values['nickname'] = nickname
    if avatar is not None:
        values['avatar'] = avatar

    try:
        with db.session.begin():
            result = db.session.execute(
                update(User).where(User.id == user_id).values(**values)
            )

        if result.rowcount == 0:
            return Err(meta="profile not found", severity=Severity.INFO)

        return Ok()
    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)