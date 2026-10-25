from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, validate_fields
from ..domain import User
from werkzeug.security import check_password_hash, generate_password_hash


def create_user(
        *,
        login: str | None = None,
        password: str | None = None,
) -> Result:
    res = validate_fields(login=login, password=password)
    login = res['login']['checked']
    password = res['password']['checked']
    if not login:
        return Err(meta=login.meta, severity=Severity.CRITICAL)
    if not password:
        return Err(meta=password.meta, severity=Severity.CRITICAL)
    login = res['login']['normal'].value
    password = generate_password_hash(res['password']['normal'].value, method="scrypt")

    try:
        user = None

        # транзакция создаёт user с login и password, также устанавливается nickname как password

    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)
    return Ok(value=user)


def authenticate(
        *,
        login: str | None = None,
        password: str | None = None,
) -> Result:
    res = validate_fields(auth_login=login, password=password)
    login = res['auth_login']['checked']
    password = res['password']['checked']
    if not login:
        return Err(meta=login.meta, severity=Severity.CRITICAL)
    if not password:
        return Err(meta=password.meta, severity=Severity.CRITICAL)
    login = res['auth_login']['normal'].value
    password = res['password']['normal'].value

    try:
        user: User = None

        # транзакция должна вернуть объект - db User, по совпадению с login, переменную назвать user

        if user is None:
            return Err(meta='Incorrect login', severity=Severity.INFO)
        stored = user.password
        if not check_password_hash(stored, password):
            return Err(meta='Incorrect password', severity=Severity.INFO)
        else:
            return Ok(value=user)
    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)

