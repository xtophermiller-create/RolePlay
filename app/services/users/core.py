from app.domain.models import User
from app.extensions import db
from app.services.commit import try_commit
from app.services.result import Err, Ok, Result
from app.services.auth import (
    hash_password,
    normalize_login,
    valid_login,
    valid_password,
    verify_password,
)

_LOGIN_MAX = 64
_NICKNAME_MAX = 64
_PASSWORD_MAX = 255


def get_user(user_id: int) -> User | None:
    return User.query.filter_by(user_id=user_id).first()


def get_user_by_login(login: str) -> User | None:
    login = (login or "").strip()
    if not login:
        return None
    return User.query.filter_by(login=login).first()


def display_name(user: User) -> str:
    """Публичное имя: nickname, иначе login."""
    nick = (user.nickname or "").strip()
    return nick or user.login


def find_user_by_handle(handle: str) -> User | None:
    """
    Найти пользователя по nickname или login.
    Сначала nickname, потом login (для приглашений в сессию).
    """
    value = (handle or "").strip()
    if not value:
        return None
    by_nick = User.query.filter(
        User.nickname == value, User.is_guest.is_(False)
    ).first()
    if by_nick:
        return by_nick
    return User.query.filter(User.login == value, User.is_guest.is_(False)).first()


def set_nickname(user_id: int, nickname: str | None) -> Result[User]:
    """
    Установить nickname. Пустое → снова = login.
    Unique среди nickname; не должен совпадать с чужим login.
    """
    user = get_user(user_id)
    if not user:
        return Err("user_not_found")

    value = (nickname or "").strip()
    if not value:
        value = user.login

    if len(value) > _NICKNAME_MAX:
        return Err("nickname_too_long")

    taken_nick = (
        User.query.filter(User.nickname == value, User.user_id != user_id).first()
    )
    if taken_nick:
        return Err("nickname_taken")

    # Нельзя взять чужой login как nickname — иначе путаница в приглашениях
    taken_login = (
        User.query.filter(User.login == value, User.user_id != user_id).first()
    )
    if taken_login:
        return Err("nickname_taken")

    user.nickname = value
    if not try_commit():
        return Err("nickname_taken")
    return Ok(user)


def change_login(user_id: int, new_login: str, current_password: str) -> Result[User]:
    """Сменить логин после повторной проверки текущего пароля."""
    user = get_user(user_id)
    if not user:
        return Err("user_not_found")

    value = normalize_login(new_login)
    if not value:
        return Err("empty_login")
    if not valid_login(value):
        return Err("invalid_login")
    if not verify_password(user, current_password or ""):
        return Err("wrong_password")
    if value == user.login:
        return Ok(user)

    taken = (
        User.query.filter(User.login == value, User.user_id != user_id).first()
    )
    if taken:
        return Err("login_taken")
    # login не должен совпасть с чужим nickname
    taken_nick = (
        User.query.filter(User.nickname == value, User.user_id != user_id).first()
    )
    if taken_nick:
        return Err("login_taken")

    old_login = user.login
    user.login = value
    # если nickname был равен старому login — синхронизируем
    if (user.nickname or "") == old_login:
        user.nickname = value
    if not try_commit():
        return Err("login_taken")
    return Ok(user)


def change_password(
    user_id: int,
    old_password: str,
    new_password: str,
    new_password_confirm: str,
) -> Result[User]:
    """Смена пароля: старый + новый дважды."""
    user = get_user(user_id)
    if not user:
        return Err("user_not_found")

    old_password = old_password or ""
    new_password = new_password or ""
    new_password_confirm = new_password_confirm or ""

    if not old_password or not new_password or not new_password_confirm:
        return Err("empty_password")
    if not verify_password(user, old_password):
        return Err("wrong_password")
    if new_password != new_password_confirm:
        return Err("password_mismatch")
    if not valid_password(new_password):
        return Err("invalid_password")
    if new_password == old_password:
        return Err("password_unchanged")

    user.password = hash_password(new_password)
    if not try_commit():
        return Err("db_commit_failed")
    return Ok(user)
