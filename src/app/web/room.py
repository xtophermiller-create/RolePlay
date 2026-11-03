from __future__ import annotations

from flask import Blueprint, abort, g, redirect, render_template, request, url_for
from ..app import limiter
from ..service.helper import Result
from ..service.room import (
    get_room, create_room, delete_room, connect, leave,
    choose_role, choose_scenario, start_session, finish_session,
)
from ..service.scenario import get_scenarios
from .auth import require_login
from .helpers import err_message, err_status, form_int, render_error
from .room_socket import broadcast_room, not_in_room

bp = Blueprint('room', __name__, url_prefix='/room')
bp.before_request(require_login)

CONNECT_LIMIT = '20 per minute'


def _render_room(code: str, *, errors: list[str] | None = None, status: int = 200):
    res = get_room(code=code)
    if not res:
        return render_error(res, status=404)
    room = res.value
    if not_in_room(room, g.user.id):
        abort(403)

    # состояние комнаты страница получает по сокету, здесь только каркас и формы
    scenarios = None
    if g.user.id == room.owner_id:
        listed = get_scenarios(user_id=g.user.id)
        if listed:
            scenarios = listed.value
        else:
            errors = [*(errors or []), err_message(listed)]
    return render_template('room/view.html', room=room, scenarios=scenarios, errors=errors), status


def _after_action(code: str, res: Result, *, next_url: str | None = None):
    ''' PRG для действий в комнате; после успеха новое состояние уходит всем участникам '''
    if not res:
        return _render_room(code, errors=[err_message(res)], status=err_status(res))
    broadcast_room(code)
    return redirect(next_url or url_for('room.view', code=code))


@bp.post('/new')
def create():
    res = create_room(user_id=g.user.id)
    if not res:
        return render_template('home.html', errors=[err_message(res)]), err_status(res)
    return redirect(url_for('room.view', code=res.value.code))


@bp.get('/join')
def join_form():
    return redirect(url_for('home.index'))


@bp.post('/join')
@limiter.limit(CONNECT_LIMIT)
def join():
    code = request.form.get('code')
    res = connect(user_id=g.user.id, code=code)
    if not res:
        return render_template('home.html', errors=[err_message(res)], code=code), err_status(res)
    broadcast_room(res.value.code)
    return redirect(url_for('room.view', code=res.value.code))


@bp.get('/<code>')
def view(code: str):
    return _render_room(code)


@bp.post('/<code>/role')
def role(code: str):
    return _after_action(code, choose_role(user_id=g.user.id, code=code, role=form_int('role')))


@bp.get('/<code>/scenario')
def scenario_form(code: str):
    res = get_room(code=code)
    if not res:
        return render_error(res, status=404)
    room = res.value
    if g.user.id != room.owner_id:
        abort(403)

    scenarios = get_scenarios(user_id=g.user.id)
    if not scenarios:
        return render_error(scenarios, status=500)
    return render_template('room/scenario.html', room=room, scenarios=scenarios.value)


@bp.post('/<code>/scenario')
def scenario(code: str):
    return _after_action(code, choose_scenario(user_id=g.user.id, code=code, scenario_id=form_int('scenario_id')))


@bp.post('/<code>/start')
def start(code: str):
    return _after_action(code, start_session(user_id=g.user.id, code=code))


@bp.post('/<code>/finish')
def finish(code: str):
    return _after_action(code, finish_session(user_id=g.user.id, code=code))


@bp.post('/<code>/leave')
def leave_room(code: str):
    return _after_action(code, leave(user_id=g.user.id, code=code), next_url=url_for('home.index'))


@bp.post('/<code>/close')
def close(code: str):
    return _after_action(code, delete_room(user_id=g.user.id, code=code), next_url=url_for('home.index'))
