from __future__ import annotations

from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, validate_fields, txn
from ..domain import User
from werkzeug.security import check_password_hash, generate_password_hash


def create_user(
        *,
        login: str | None = None,
        password: str | None = None,
) -> Result[User]:
    ''' Это типа регистрация, но по сути ведь создание пользователя :) '''
    # сразу отправляем все на валидацию и хеширование
    res = validate_fields(login=login, password=password)
    res_login, res_password = res['login']['checked'], res['password']['checked']
    if not res_login:
        return Err(meta=f'Validation errors: {res_login.meta}')
    if not res_password:
        return Err(meta=f'Validation errors: {res_password.meta}')
    login, password = res['login']['normal'].value, generate_password_hash(res['password']['normal'].value, method="scrypt")

    # заключаем транзакцию в try
    try:
        with txn() as s:
            user = s.execute(
                insert(User).values(login=login, password=password).returning(User)
            ).scalar_one()

        if user is None:
            return Err(meta="User not found", severity=Severity.INFO)

        return Ok(value=user)

    # критическая ошибка транзакции
    except SQLAlchemyError as e:
        return Err(meta=f"Database transaction failed : {e}", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception as e:
        return Err(meta=f"Unexpected transaction error : {e}", severity=Severity.CRITICAL)


def authenticate(
        *,
        login: str | None = None,
        password: str | None = None,
) -> Result[User]:
    ''' Авторизация '''
    # сразу отправляем все на валидацию и хеширование
    res = validate_fields(auth_login=login, password=password)
    res_login, res_password = res['auth_login']['checked'], res['password']['checked']
    if not res_login:
        return Err(meta=f'Validation errors: {res_login.meta}')
    if not res_password:
        return Err(meta=f'Validation errors: {res_password.meta}')
    login, password = res['auth_login']['normal'].value, res['password']['normal'].value

    # заключаем транзакцию в try
    try:
        with txn() as s:
            user = s.execute(
                select(User).where(User.login == login)
            ).scalar_one_or_none()

            stored = user.password if user is not None else None

        if user is None:
            return Err(meta='Incorrect login', severity=Severity.INFO)
        if not check_password_hash(stored, password):
            return Err(meta='Incorrect password', severity=Severity.INFO)

        return Ok(value=user)

    # критическая ошибка транзакции
    except SQLAlchemyError as e:
        return Err(meta=f"Database transaction failed : {e}", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception as e:
        return Err(meta=f"Unexpected transaction error : {e}", severity=Severity.CRITICAL)