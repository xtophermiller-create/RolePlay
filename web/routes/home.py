from flask import Blueprint, jsonify, render_template, request, session, url_for

from app.auth_utils import registered_required
from app.services.users import get_user, set_nickname
from web.routes.profile import avatar_url, default_avatar_url

bp = Blueprint("home", __name__, url_prefix="/home")

_NICK_ERRORS = {
    "user_not_found": ("Пользователь не найден", 404),
    "nickname_too_long": ("Слишком длинный nickname", 400),
    "nickname_taken": ("Этот nickname уже занят", 409),
    "db_commit_failed": ("Не удалось сохранить", 500),
}


@bp.route("/")
@registered_required
def index():
    user = get_user(session["user_id"])
    return render_template(
        "home.html",
        nickname=(user.nickname if user else None) or "",
        login=(user.login if user else None) or session.get("login") or "",
        avatar_url=avatar_url(user),
        default_avatar_url=default_avatar_url(),
        api={
            "nickname": url_for("home.api_nickname"),
            "avatar": url_for("profile.avatar_file"),
            "login": url_for("profile.api_change_login"),
            "password": url_for("profile.api_change_password"),
        },
    )


@bp.route("/api/nickname", methods=["POST"])
@registered_required
def api_nickname():
    data = request.get_json(silent=True) or {}
    result = set_nickname(session["user_id"], data.get("nickname"))
    if not result:
        message, status = _NICK_ERRORS.get(
            result.error, ("Не удалось сохранить", 400)
        )
        return jsonify({"ok": False, "error": result.error, "message": message}), status

    return jsonify({"ok": True, "nickname": result.value.nickname or ""})
