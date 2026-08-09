from functools import wraps

from flask import flash, jsonify, redirect, request, session, url_for


def is_guest_session() -> bool:
    return bool(session.get("is_guest"))


def guest_home_endpoint() -> str:
    return "sessions.join_page"


def _wants_json() -> bool:
    path = request.path or ""
    if "/api/" in path:
        return True
    if request.is_json:
        return True
    best = request.accept_mimetypes.best
    return best == "application/json"


def _unauthenticated_response():
    if _wants_json():
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "unauthorized",
                    "message": "Требуется вход",
                }
            ),
            401,
        )
    return redirect(url_for("auth.login"))


def _guests_forbidden_response():
    if _wants_json():
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "guests_forbidden",
                    "message": "Гость может только присоединиться к сессии по коду",
                }
            ),
            403,
        )
    flash("Гость может только войти в сессию по коду", "error")
    return redirect(url_for(guest_home_endpoint()))


def _load_session_user():
    """Проверить cookie-сессию; для гостя — TTL. Возвращает User или None."""
    from app.services import guests as guests_service
    from app.services.users import get_user

    uid = session.get("user_id")
    if uid is None:
        return None

    user = get_user(uid)
    if not user:
        session.clear()
        return None

    if getattr(user, "is_guest", False):
        guests_service.maybe_purge_expired()
        if guests_service.is_expired(user):
            guests_service.delete_guest(user)
            session.clear()
            flash("Гостевая сессия истекла — войдите снова", "error")
            return None
        session["is_guest"] = True
        session["login"] = user.login
    else:
        session["is_guest"] = False

    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if _load_session_user() is None:
            return _unauthenticated_response()
        return view(*args, **kwargs)

    return wrapped


def registered_required(view):
    """Только полноценный аккаунт (не гость)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = _load_session_user()
        if user is None:
            return _unauthenticated_response()
        if getattr(user, "is_guest", False) or is_guest_session():
            return _guests_forbidden_response()
        return view(*args, **kwargs)

    return wrapped
