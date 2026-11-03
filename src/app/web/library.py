from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, url_for
from ..service.scenario import create_scenario, delete_scenario, get_scenarios
from .auth import require_login
from .helpers import err_message, err_status

bp = Blueprint('library', __name__, url_prefix='/library')
bp.before_request(require_login)


def _render_library(*, errors: list[str] | None = None, status: int = 200):
    errors = list(errors or [])
    scenarios = get_scenarios(user_id=g.user.id)
    if not scenarios:
        errors.append(err_message(scenarios))
    return render_template('library.html', scenarios=scenarios.value, errors=errors), status


@bp.get('')
def index():
    return _render_library()


@bp.post('/new')
def create():
    res = create_scenario(user_id=g.user.id, title=request.form.get('title'))
    if not res:
        return _render_library(errors=[err_message(res)], status=err_status(res))
    return redirect(url_for('editor.edit', scenario_id=res.value.id))


@bp.post('/<int:scenario_id>/delete')
def delete(scenario_id: int):
    res = delete_scenario(user_id=g.user.id, scenario_id=scenario_id)
    if not res:
        return _render_library(errors=[err_message(res)], status=err_status(res))
    return redirect(url_for('library.index'))
