import secrets

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app.auth_utils import is_guest_session
from app.security import verify_turnstile
from app.services import auth as auth_service
from app.services import auth_throttle
from app.services import guests as guests_service

bp = Blueprint("auth", __name__)

_REGISTER_ERRORS = {
    "invalid_login": "Логин: 3–64 символа, латиница/цифры и ._@-",
    "invalid_password": f"Пароль: минимум {auth_service.PASSWORD_MIN} символов",
    "login_taken": "Этот логин уже занят",
}


@bp.route("/register", methods=["GET", "POST"])
def register():
    mode = current_app.config["REGISTRATION_MODE"]
    if mode not in {"open", "invite", "closed"}:
        mode = "closed"
    if mode == "closed":
        flash("Регистрация временно закрыта", "error")
        return render_template("register.html", registration_closed=True), 403
    if request.method == "POST":
        login = request.form.get("login", "")
        ip = request.remote_addr or "unknown"
        blocked, _ = auth_throttle.status("register", ip, login)
        if blocked:
            flash("Слишком много попыток — подождите и попробуйте снова", "error")
            return render_template("register.html", registration_mode=mode), 429

        invite_ok = mode != "invite" or secrets.compare_digest(
            request.form.get("invite_code", ""),
            current_app.config["REGISTRATION_INVITE_CODE"],
        )
        captcha_ok = verify_turnstile(
            request.form.get("cf-turnstile-response", ""), ip
        )
        if not invite_ok:
            auth_throttle.record_failure("register", ip, login)
            flash("Неверный код приглашения", "error")
            return render_template("register.html", registration_mode=mode), 400
        if not captcha_ok:
            auth_throttle.record_failure("register", ip, login)
            flash("Подтвердите, что вы не робот", "error")
            return render_template("register.html", registration_mode=mode), 400

        result = auth_service.register(login, request.form.get("password", ""))
        if result:
            auth_throttle.clear("register", ip, login)
            flash("Аккаунт создан — можно войти", "success")
            return redirect(url_for("auth.login"))

        # Валидация / занятый логин — не жжём throttle как брутфорс
        if result.error == "login_taken":
            auth_throttle.record_failure("register", ip, login)
        flash(_REGISTER_ERRORS.get(result.error, "Не удалось зарегистрироваться"), "error")
        return render_template("register.html", registration_mode=mode)

    return render_template("register.html", registration_mode=mode)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form.get("login", "")
        ip = request.remote_addr or "unknown"
        blocked, failures = auth_throttle.status("login", ip, login)
        if blocked:
            flash("Слишком много попыток — подождите и попробуйте снова", "error")
            return render_template("login.html", show_turnstile=True), 429

        needs_captcha = failures >= 2
        captcha_ok = not needs_captcha or verify_turnstile(
            request.form.get("cf-turnstile-response", ""), ip
        )
        if not captcha_ok:
            auth_throttle.record_failure("login", ip, login)
            flash("Подтвердите, что вы не робот", "error")
            return render_template("login.html", show_turnstile=True), 400

        ok, user = auth_service.authenticate(
            login,
            request.form.get("password", ""),
        )
        if not ok:
            failures = auth_throttle.record_failure("login", ip, login)
            flash("Неверный логин или пароль", "error")
            return render_template("login.html", show_turnstile=failures >= 2)

        auth_throttle.clear("login", ip, login)
        session.clear()
        session.permanent = True
        session["user_id"] = user.user_id
        session["login"] = user.login
        session["is_guest"] = False
        return redirect(url_for("home.index"))

    return render_template("login.html")


@bp.route("/guest", methods=["POST"])
def guest_login():
    """Войти как гость → только страница ввода кода сессии."""
    ip = request.remote_addr or "unknown"
    blocked, _ = auth_throttle.status("guest", ip, "")
    if blocked:
        flash("Слишком много попыток — подождите и попробуйте снова", "error")
        return redirect(url_for("auth.login")), 429

    guests_service.maybe_purge_expired()
    result = guests_service.create_guest()
    if not result:
        auth_throttle.record_failure("guest", ip, "")
        flash("Не удалось создать гостевой вход", "error")
        return redirect(url_for("auth.login"))

    auth_throttle.clear("guest", ip, "")
    user = result.value
    session.clear()
    session.permanent = True
    session["user_id"] = user.user_id
    session["login"] = user.login
    session["is_guest"] = True
    return redirect(url_for("sessions.join_page"))


@bp.route("/logout", methods=["POST"])
def logout():
    uid = session.get("user_id")
    was_guest = is_guest_session() or bool(session.get("is_guest"))
    session.clear()
    if was_guest and uid is not None:
        guests_service.delete_guest(uid)
    return redirect(url_for("auth.login"))
