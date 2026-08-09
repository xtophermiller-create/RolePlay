"""Оболочка приложения: корневой `/` и общие переменные шаблонов."""

from __future__ import annotations

import os

from flask import Flask, redirect, session, url_for


def register_app_shell(app: Flask) -> None:
    @app.context_processor
    def inject_nav_profile():
        from app.auth_utils import is_guest_session
        from app.services import users as users_service

        default = url_for("static", filename="icons/ui/dis-avatar.svg")
        uid = session.get("user_id")
        guest = bool(session.get("is_guest") or is_guest_session())
        if uid is None:
            return {"nav_avatar_url": default, "is_guest": False}
        user = users_service.get_user(uid)
        if user is not None:
            guest = bool(getattr(user, "is_guest", False))
        if user and user.avatar:
            token = os.path.basename(str(user.avatar)).replace(".", "_")
            return {
                "nav_avatar_url": url_for("profile.avatar_file", v=token),
                "is_guest": guest,
            }
        return {"nav_avatar_url": default, "is_guest": guest}

    @app.route("/")
    def index():
        from app.auth_utils import is_guest_session

        if session.get("user_id") is not None:
            if is_guest_session() or session.get("is_guest"):
                return redirect(url_for("sessions.join_page"))
            return redirect(url_for("home.index"))
        return redirect(url_for("auth.login"))
