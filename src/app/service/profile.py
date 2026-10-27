from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, validate_fields
from ..domain import USER_LENGTH


def get_profile(
        *,
        user_id: int | None = None,
) -> Result[tuple[str, str]]:
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)

    try:
        nickname, avatar = None, None

        # транзакция достаёт из строки с совпадающим user_id из users общедоступные данные: nickname и avatar. 

        return Ok(value=(nickname, avatar))
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

    if all(value is None for value in (nickname, avatar)):
        return Ok(meta="No fields to update")
    if not isinstance(nickname, str | None) or not isinstance(avatar, str | None):
        return Err(meta="One or more fields have invalid types", severity=Severity.ERROR)
    if nickname is not None and not nickname:
        login = None
        try:

            # транзакция на получение login от userid

        except SQLAlchemyError as e:
            return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
        except Exception as e:
            return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)
        nickname = login

    for length, field, field_name in zip(
        [LENGTH_NICKNAME, LENGTH_AVATAR],
        [nickname, avatar],
        ['nickname', 'avatar'],
    ):
        if isinstance(field, str):
            if len(field.strip()) > length:
                return Err(meta=f"{field_name} exceeds maximum length", severity=Severity.ERROR)

    try:

        # транзакция

    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)


def delete_profile(
        *,
        user_id: int | None = None,
) -> Result:
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)

    try:

        # транзакция проверяет user_id с owner_id в записи db, если всё ок, удаляет сценарий

        return Ok()
    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)