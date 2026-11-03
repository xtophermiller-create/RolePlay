from __future__ import annotations

from flask import Blueprint, g, render_template
from ..service.session import get_session, get_sessions
from .auth import require_login
from .helpers import render_error

bp = Blueprint('history', __name__, url_prefix='/history')
bp.before_request(require_login)


@bp.get('')
def index():
    res = get_sessions(user_id=g.user.id)
    if not res:
        return render_error(res, status=500)
    return render_template('history/list.html', sessions=res.value)


@bp.get('/<int:session_id>')
def detail(session_id: int):
    res = get_session(user_id=g.user.id, session_id=session_id)
    if not res:
        return render_error(res, status=404)
    return render_template('history/detail.html', record=res.value)
