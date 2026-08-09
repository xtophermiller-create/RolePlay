"""Сессии: API + страницы выбора сценария / лобби / присоединения."""

from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth_utils import is_guest_session, login_required, registered_required
from app.domain.models.rp_session import STATUS_CANCELLED, STATUS_LOBBY
from app.services import sessions as sessions_service
from app.services.scenarios import list_scenarios
from app.services.sessions import participants as participants_service
from app.services.users import get_user
from web.routes.profile import avatar_url, default_avatar_url

bp = Blueprint("sessions", __name__, url_prefix="/sessions")


def _json_error(code: str, message: str, status: int = 400):
    return jsonify({"ok": False, "error": code, "message": message}), status


_ERRORS = {
    "user_not_found": ("Пользователь не найден", 404),
    "scenario_not_found": ("Сценарий не найден", 404),
    "scenario_file_missing": ("Файл сценария недоступен", 400),
    "scenario_snapshot_failed": ("Не удалось зафиксировать сценарий", 400),
    "not_found": ("Не найдено", 404),
    "invalid_status": ("Недопустимый статус сессии", 400),
    "session_closed": ("Сессия закрыта", 400),
    "session_full": ("В сессии слишком много участников", 400),
    "host_cannot_leave": ("Хост не может выйти — отмените сессию", 400),
    "cannot_leave_active": ("Нельзя выйти из активной сессии", 400),
    "not_participant": ("Вы не в этой сессии", 403),
    "invalid_role": ("Неизвестная роль", 400),
    "role_taken": ("Роль уже занята", 409),
    "roles_not_ready": ("Нужно по одному игроку в роли 1 и роли 2", 400),
    "not_started": ("Сессия ещё не запущена", 400),
    "forbidden": ("Нет прав на это действие", 403),
    "empty_code": ("Введите ключ сессии", 400),
    "db_commit_failed": ("Не удалось сохранить", 500),
    "guests_forbidden": ("Гость может только присоединиться к сессии по коду", 403),
}


def _err(code: str):
    msg, status = _ERRORS.get(code, ("Ошибка", 400))
    return _json_error(code, msg, status)


def _enrich_participants(payload: dict) -> dict:
    for p in payload.get("participants") or []:
        user = get_user(p.get("user_id"))
        p["avatar_url"] = avatar_url(user)
    return payload


def _session_payload(row) -> dict:
    payload = _enrich_participants(sessions_service.session_to_dict(row))
    # Чтобы лобби всегда могло обновить роли/название без отдельного поля.
    payload["role_labels"] = _role_labels(row)
    return payload


def _fallback_home():
    if is_guest_session():
        return url_for("sessions.join_page")
    return url_for("home.index")


def _role_labels(row) -> dict:
    try:
        doc = sessions_service.scenario_document(row)
        roles = doc.get("roles") or {}
    except (TypeError, ValueError, KeyError):
        roles = {}
    return {
        "actor1": (roles.get("actor1") or {}).get("label") or "Роль 1",
        "actor2": (roles.get("actor2") or {}).get("label") or "Роль 2",
        "observer": "Наблюдатель",
    }


def _can_view(row, user_id: int) -> bool:
    if not row:
        return False
    if row.host_user_id == user_id:
        return True
    return bool(sessions_service.get_participant(row.session_id, user_id))


# ——— HTML pages ———


@bp.get("/new")
@registered_required
def pick_scenario():
    scenarios = list_scenarios(session["user_id"])
    return render_template(
        "session_pick.html",
        scenarios=scenarios,
        api={
            "create": url_for("sessions.api_create"),
            "lobby": url_for("sessions.lobby", session_id=0).replace("/0", "/{id}"),
        },
    )


@bp.get("/join")
@login_required
def join_page():
    guest = is_guest_session()
    return render_template(
        "session_join.html",
        is_guest=guest,
        api={
            "join": url_for("sessions.api_join"),
            "lobby": url_for("sessions.lobby", session_id=0).replace("/0", "/{id}"),
            "logout": url_for("auth.logout"),
        },
    )


@bp.get("/<int:session_id>")
@login_required
def lobby(session_id: int):
    row = sessions_service.get_session(session_id)
    user_id = session["user_id"]
    if not row or not _can_view(row, user_id):
        flash("Сессия не найдена", "error")
        return redirect(_fallback_home())

    guest = is_guest_session()
    is_host = row.host_user_id == user_id
    payload = _session_payload(row)
    host_scenarios = list_scenarios(user_id) if is_host and not guest else []
    return render_template(
        "session_lobby.html",
        session_row=row,
        session_data=payload,
        role_labels=_role_labels(row),
        scenarios=host_scenarios,
        current_user_id=user_id,
        is_host=is_host,
        is_guest=guest,
        default_avatar_url=default_avatar_url(),
        crown_url=url_for("static", filename="icons/ui/crown.svg"),
        api={
            "get": url_for("sessions.api_get", session_id=session_id),
            "ping": url_for("sessions.api_ping", session_id=session_id),
            "role": url_for("sessions.api_choose_role", session_id=session_id),
            "scenario": url_for("sessions.api_set_scenario", session_id=session_id),
            "start": url_for("sessions.api_start", session_id=session_id),
            "play_page": url_for("sessions.play", session_id=session_id),
            "cancel": url_for("sessions.api_cancel", session_id=session_id),
            "leave": url_for("sessions.api_leave", session_id=session_id),
            "home": _fallback_home(),
            "join": url_for("sessions.join_page"),
        },
    )


@bp.get("/<int:session_id>/play")
@login_required
def play(session_id: int):
    row = sessions_service.get_session(session_id)
    user_id = session["user_id"]
    if not row or not _can_view(row, user_id):
        flash("Сессия не найдена", "error")
        return redirect(_fallback_home())

    if row.status == STATUS_LOBBY:
        return redirect(url_for("sessions.lobby", session_id=session_id))
    if row.status == STATUS_CANCELLED:
        flash("Сессия отменена", "error")
        return redirect(_fallback_home())

    guest = is_guest_session()
    payload = _session_payload(row)
    return render_template(
        "session_play.html",
        session_row=row,
        session_data=payload,
        role_labels=_role_labels(row),
        current_user_id=user_id,
        is_host=row.host_user_id == user_id,
        is_guest=guest,
        default_avatar_url=default_avatar_url(),
        api={
            "play": url_for("sessions.api_play", session_id=session_id),
            "ping": url_for("sessions.api_ping", session_id=session_id),
            "ready": url_for("sessions.api_ready", session_id=session_id),
            "complete": url_for("sessions.api_complete", session_id=session_id),
            "restart": url_for("sessions.api_restart", session_id=session_id),
            "home": _fallback_home(),
            "lobby": url_for("sessions.lobby", session_id=session_id),
        },
    )


# ——— API ———


@bp.post("/api/create")
@registered_required
def api_create():
    data = request.get_json(silent=True) or {}
    try:
        scenario_id = int(data.get("scenario_id"))
    except (TypeError, ValueError):
        return _json_error("invalid_scenario", "Укажите scenario_id", 400)
    result = sessions_service.create_session(session["user_id"], scenario_id)
    if not result:
        return _err(result.error)
    row = result.value
    return jsonify(
        {
            "ok": True,
            "session": _session_payload(row),
            "lobby_url": url_for("sessions.lobby", session_id=row.session_id),
        }
    )


@bp.post("/api/join")
@login_required
def api_join():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return _err("empty_code")
    row = sessions_service.get_session_by_code(code)
    if not row:
        return _err("not_found")
    result = participants_service.add_participant(row.session_id, session["user_id"])
    if not result:
        return _err(result.error)
    return jsonify(
        {
            "ok": True,
            "session": _session_payload(row),
            "lobby_url": url_for("sessions.lobby", session_id=row.session_id),
        }
    )


@bp.get("/api/<int:session_id>")
@login_required
def api_get(session_id: int):
    row = sessions_service.get_session(session_id)
    if not row:
        return _err("not_found")
    if not _can_view(row, session["user_id"]):
        return _err("not_participant")
    return jsonify(
        {
            "ok": True,
            "session": _session_payload(row),
            "role_labels": _role_labels(row),
        }
    )


@bp.post("/api/<int:session_id>/ping")
@login_required
def api_ping(session_id: int):
    """Обновить снимок лобби/боя (без presence-таймеров)."""
    result = participants_service.heartbeat(session_id, session["user_id"])
    if not result:
        return _err(result.error)
    row = result.value
    return jsonify(
        {
            "ok": True,
            "session": _session_payload(row),
            "role_labels": _role_labels(row),
        }
    )


@bp.post("/api/<int:session_id>/role")
@login_required
def api_choose_role(session_id: int):
    data = request.get_json(silent=True) or {}
    role = data.get("role", None)
    if role == "" or role is False:
        role = None
    result = participants_service.choose_role(session_id, session["user_id"], role)
    if not result:
        return _err(result.error)
    return jsonify(
        {
            "ok": True,
            "participant": sessions_service.participant_to_dict(result.value),
        }
    )


@bp.post("/api/<int:session_id>/scenario")
@registered_required
def api_set_scenario(session_id: int):
    """Сменить сценарий в лобби (только хост, только status=lobby)."""
    data = request.get_json(silent=True) or {}
    try:
        scenario_id = int(data.get("scenario_id"))
    except (TypeError, ValueError):
        return _json_error("invalid_scenario", "Укажите scenario_id", 400)
    result = sessions_service.set_session_scenario(
        session_id, session["user_id"], scenario_id
    )
    if not result:
        return _err(result.error)
    row = result.value
    return jsonify(
        {
            "ok": True,
            "session": _session_payload(row),
            "role_labels": _role_labels(row),
        }
    )


@bp.post("/api/<int:session_id>/start")
@registered_required
def api_start(session_id: int):
    result = sessions_service.start_session(session_id, session["user_id"])
    if not result:
        return _err(result.error)
    return jsonify(
        {
            "ok": True,
            "session": _session_payload(result.value),
            "play_url": url_for("sessions.play", session_id=session_id),
        }
    )


@bp.get("/api/<int:session_id>/play")
@login_required
def api_play(session_id: int):
    result = sessions_service.play_payload(session_id, session["user_id"])
    if not result:
        return _err(result.error)
    payload = result.value
    payload["session"] = _enrich_participants(payload["session"])
    return jsonify({"ok": True, **payload})


@bp.post("/api/<int:session_id>/ready")
@login_required
def api_ready(session_id: int):
    """Актёр подтверждает готовность (started → ready, когда оба готовы)."""
    result = participants_service.mark_ready(session_id, session["user_id"])
    if not result:
        return _err(result.error)
    row = result.value
    return jsonify(
        {
            "ok": True,
            "session": _session_payload(row),
            "actors_ready": sessions_service.actors_ready(session_id),
            "my_ready": True,
        }
    )


@bp.post("/api/<int:session_id>/complete")
@registered_required
def api_complete(session_id: int):
    """Завершить бой (хост)."""
    result = sessions_service.finish_session(session_id, session["user_id"])
    if not result:
        return _err(result.error)
    return jsonify({"ok": True, "session": _session_payload(result.value)})


@bp.post("/api/<int:session_id>/restart")
@registered_required
def api_restart(session_id: int):
    """finished → lobby (только хост)."""
    result = sessions_service.reopen_session(session_id, session["user_id"])
    if not result:
        return _err(result.error)
    return jsonify(
        {
            "ok": True,
            "session": _session_payload(result.value),
            "lobby_url": url_for("sessions.lobby", session_id=session_id),
        }
    )


@bp.post("/api/<int:session_id>/cancel")
@registered_required
def api_cancel(session_id: int):
    result = sessions_service.cancel_session(session_id, session["user_id"])
    if not result:
        return _err(result.error)
    return jsonify({"ok": True, "session": _session_payload(result.value)})


@bp.post("/api/<int:session_id>/leave")
@login_required
def api_leave(session_id: int):
    result = participants_service.leave_session(session_id, session["user_id"])
    if not result:
        return _err(result.error)
    return jsonify({"ok": True})
