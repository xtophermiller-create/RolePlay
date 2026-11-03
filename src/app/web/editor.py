from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, url_for
from ..service.draft import open_draft
from .auth import require_login
from .helpers import render_error

bp = Blueprint('editor', __name__, url_prefix='/editor')
bp.before_request(require_login)


@bp.get('')
def index():
    return redirect(url_for('library.index'))


@bp.get('/<int:scenario_id>')
def edit(scenario_id: int):
    # содержимое черновика страница получает по сокету, здесь только каркас
    res = open_draft(user_id=g.user.id, scenario_id=scenario_id)
    if not res:
        return render_error(res, status=404)
    return render_template('editor.html', scenario_id=scenario_id)
