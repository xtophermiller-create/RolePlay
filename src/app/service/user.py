from __future__ import annotations

from .helper import Result, Err, Ok, Severity, validate_fields, txn
from ..domain import User

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import secrets
from werkzeug.security import check_password_hash, generate_password_hash

# Тот же scrypt, что у настоящих паролей: сравнение занимает столько же времени, если логина нет.
_DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_urlsafe(32), method="scrypt")


def create_user(
        *,
        login: str | None = None,
        password: str | None = None,
) -> Result[tuple]:
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

        return Ok(value=(user.id, user.login, user.nickname, user.avatar, user.is_admin, user.is_guest))

    except IntegrityError:
        return Err(meta="Login is taken", severity=Severity.INFO)
    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


def authenticate(
        *,
        login: str | None = None,
        password: str | None = None,
) -> Result[tuple]:
    ''' Авторизация '''
    # сразу отправляем все на валидацию
    res = validate_fields(auth_login=login, password=password)
    res_login, res_password = res['auth_login']['checked'], res['password']['checked']
    if not res_login:
        return Err(meta=f'Validation errors: {res_login.meta}')
    if not res_password:
        return Err(meta=f'Validation errors: {res_password.meta}')
    login, password = res['auth_login']['normal'].value, res['password']['normal'].value

    # чтение и проверка пароля не пишут в базу; время входа — только после совпадения
    try:
        with txn() as s:
            user = s.execute(
                select(User).where(User.login == login)
            ).scalar_one_or_none()
            stored = user.password if user is not None else _DUMMY_PASSWORD_HASH

        password_matches = check_password_hash(stored, password)
        if user is None or not password_matches:
            return Err(meta='Incorrect login or password', severity=Severity.INFO)

        with txn() as s:
            row = s.execute(
                update(User).where(User.id == user.id).values(last_login_at=func.now())
            )

        if row.rowcount == 0:
            return Err(meta="User not found", severity=Severity.INFO)

        return Ok(value=(user.id, user.login, user.nickname, user.avatar, user.is_admin, user.is_guest))

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


def change_password(
        *,
        user_id: int | None = None,
        old_password: str | None = None,
        new_password: str | None = None,
) -> Result:
    # проверяем user_id на тип int
    if type(user_id) is not int:
        return Err(meta='user_id is not int', severity=Severity.ERROR)

    # сразу отправляем все на валидацию
    res1 = validate_fields(password=old_password)
    res2 = validate_fields(password=new_password)
    res_old_pas, res_new_pas = res1['password']['checked'], res2['password']['checked']
    if not res_old_pas:
        return Err(meta=f'Validation errors: {res_old_pas.meta}')
    if not res_new_pas:
        return Err(meta=f'Validation errors: {res_new_pas.meta}')
    old_pas, new_pas = res1['password']['normal'].value, res2['password']['normal'].value

    try:
        with txn() as s:
            user = s.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            stored = user.password if user is not None else _DUMMY_PASSWORD_HASH

        password_matches = check_password_hash(stored, old_pas)
        if user is None or not password_matches:
            return Err(meta='Incorrect password', severity=Severity.INFO)

        new_pas = generate_password_hash(new_pas, method="scrypt")

        with txn() as s:
            row = s.execute(
                update(User)
                .where(User.id == user_id, User.password == stored)
                .values(password=new_pas)
            )

        if row.rowcount == 0:
            return Err(meta="User not found", severity=Severity.INFO)

        return Ok()

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


def change_login(
        *,
        user_id: int | None = None,
        password: str | None = None,
        new_login: str | None = None,
) -> Result:
    if type(user_id) is not int:
        return Err(meta='user_id is not int', severity=Severity.ERROR)

    res = validate_fields(login=new_login, password=password)
    res_login, res_password = res['login']['checked'], res['password']['checked']
    if not res_login:
        return Err(meta=f'Validation errors: {res_login.meta}')
    if not res_password:
        return Err(meta=f'Validation errors: {res_password.meta}')
    login, password = res['login']['normal'].value, res['password']['normal'].value

    try:
        with txn() as s:
            user = s.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            stored = user.password if user is not None else _DUMMY_PASSWORD_HASH

        password_matches = check_password_hash(stored, password)
        if user is None or not password_matches:
            return Err(meta='Incorrect password', severity=Severity.INFO)

        with txn() as s:
            row = s.execute(
                update(User)
                .where(User.id == user_id, User.password == stored)
                .values(login=login)
            )

        if row.rowcount == 0:
            return Err(meta='Incorrect password', severity=Severity.INFO)

        return Ok()

    except IntegrityError:
        return Err(meta="Login is taken", severity=Severity.INFO)
    except SQLAlchemyError:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)