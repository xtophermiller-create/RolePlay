"""Профиль: раздача / загрузка / удаление аватара (как в life_core)."""

from __future__ import annotations

import os

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    send_file,
    session,
    url_for,
)

from app.auth_utils import login_required, registered_required
from app.services import media as media_service
from app.services import users as users_service

bp = Blueprint("profile", __name__, url_prefix="/profile")


def _json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def default_avatar_url() -> str:
    return url_for("static", filename="icons/ui/dis-avatar.svg")


def avatar_url(user) -> str:
    if user and user.avatar:
        token = os.path.basename(str(user.avatar)).replace(".", "_")
        if getattr(user, "user_id", None) and user.user_id != session.get("user_id"):
            return url_for("profile.avatar_of_user", user_id=user.user_id, v=token)
        return url_for("profile.avatar_file", v=token)
    return default_avatar_url()


def _send_user_avatar(user):
    abs_path = media_service.user_avatar_abs_path(user)
    if not abs_path:
        return current_app.send_static_file("icons/ui/dis-avatar.svg")
    return send_file(abs_path, mimetype="image/jpeg", max_age=3600)


@bp.route("/avatar", methods=["GET", "POST", "DELETE"])
@login_required
def avatar_file():
    user_id = session["user_id"]
    user = users_service.get_user(user_id)
    if not user:
        return _json_error("Пользователь не найден", 404)

    if request.method in ("POST", "DELETE"):
        if getattr(user, "is_guest", False):
            return _json_error("Гость не может менять профиль", 403)
        if request.method == "DELETE":
            media_service.delete_user_avatar(user_id)
            user = users_service.get_user(user_id)
            return jsonify({"ok": True, "avatar_url": avatar_url(user)})
        upload = request.files.get("avatar")
        if not media_service.set_user_avatar(user_id, upload):
            return _json_error("Не удалось загрузить аватар")
        user = users_service.get_user(user_id)
        return jsonify({"ok": True, "avatar_url": avatar_url(user)})

    return _send_user_avatar(user)


@bp.route("/avatar/user/<int:user_id>")
@login_required
def avatar_of_user(user_id: int):
    """Аватар любого пользователя (для лобби сессий)."""
    user = users_service.get_user(user_id)
    if not user:
        return current_app.send_static_file("icons/ui/dis-avatar.svg")
    return _send_user_avatar(user)


_ACCOUNT_ERRORS = {
    "user_not_found": ("Пользователь не найден", 404),
    "empty_login": ("Введите логин", 400),
    "login_too_long": ("Логин слишком длинный", 400),
    "invalid_login": ("Логин: 3–64 символа, буквы, цифры и ._-@", 400),
    "login_taken": ("Этот логин уже занят", 400),
    "empty_password": ("Заполните все поля пароля", 400),
    "wrong_password": ("Неверный текущий пароль", 400),
    "password_mismatch": ("Новые пароли не совпадают", 400),
    "password_too_long": ("Пароль слишком длинный", 400),
    "invalid_password": ("Пароль должен содержать от 12 до 255 символов", 400),
    "password_unchanged": ("Новый пароль совпадает со старым", 400),
    "db_commit_failed": ("Не удалось сохранить", 400),
}


@bp.route("/login", methods=["POST"])
@registered_required
def api_change_login():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    result = users_service.change_login(
        user_id, data.get("login", ""), data.get("current_password", "")
    )
    if not result:
        msg, status = _ACCOUNT_ERRORS.get(
            result.error, ("Не удалось сменить логин", 400)
        )
        return _json_error(msg, status)
    session["login"] = result.value.login
    return jsonify({"ok": True, "login": result.value.login})


@bp.route("/password", methods=["POST"])
@registered_required
def api_change_password():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    result = users_service.change_password(
        user_id,
        data.get("old_password", ""),
        data.get("new_password", ""),
        data.get("new_password_confirm", ""),
    )
    if not result:
        msg, status = _ACCOUNT_ERRORS.get(
            result.error, ("Не удалось сменить пароль", 400)
        )
        return _json_error(msg, status)
    return jsonify({"ok": True})
