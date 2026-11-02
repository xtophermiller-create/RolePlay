from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, validate_fields, txn
from ..domain import User


def get_profile(
        *,
        user_id: int | None = None,
) -> Result[tuple[str | None, str | None]]:
    ''' Возвращает по user_id : nickname и avatar '''
    # проверка user_id на тип int
    if type(user_id) is not int:
        return Err(meta="user_id is not integer", severity=Severity.ERROR)

    # начало транзакции заключаем в try
    try:
        with txn() as s:
            user = s.execute(
                select(User.nickname, User.avatar).where(User.id == user_id),
            ).one_or_none()

        if user is None:
            return Err(meta="Profile not found", severity=Severity.INFO)

        return Ok(value=(user.nickname, user.avatar))

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


@dataclass(frozen=True)
class PatchProfile:
    nickname: str | None = None
    avatar: str | None = None

def update_profile(
        *,
        user_id: int | None = None,
        patch: PatchProfile | None = None,
) -> Result:
    ''' Обновляет avatar и nickname в профиле '''
    # проверка user_id на тип int
    if type(user_id) is not int:
        return Err(meta="user_id is not integer", severity=Severity.ERROR)
    # проверка patch на тип PatchProfile
    if type(patch) is not PatchProfile:
        return Err(meta="patch is not PatchProfile", severity=Severity.ERROR)

    # отправляем patch fields на валидацию и обрабатываем результат
    res = validate_fields(nickname=patch.nickname, avatar=patch.avatar)
    res_nickname, res_avatar = res['nickname']['checked'], res['avatar']['checked']
    errors = []
    for x in [res_nickname, res_avatar]:
        if not x:
            errors.append(x.meta)
    if errors:
        return Err(meta='Validation errors: ' + ' | '.join(errors), severity=Severity.ERROR)
    nickname, avatar = res['nickname']['normal'].value, res['avatar']['normal'].value

    # если все поля None - значит ничего менять не нужно, это не ошибка
    if all(value is None for value in (nickname, avatar)):
        return Ok(meta="No fields to update")

    # соединяем fields которые not None
    values = {}
    if nickname is not None:
        values['nickname'] = nickname
    if avatar is not None:
        values['avatar'] = avatar

    # начало транзакции заключаем в try
    try:
        with txn() as s:
            row = s.execute(
                update(User).where(User.id == user_id).values(**values)
            )

        if row.rowcount == 0:
            return Err(meta="Profile not found", severity=Severity.INFO)

        return Ok()

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)