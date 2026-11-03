from __future__ import annotations

from flask import Blueprint, g, render_template
from ..service.profile import get_profile
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
    sessions = list(res.value or [])
    sessions.sort(key=lambda record: record.created_at, reverse=True)
    return render_template('history/list.html', sessions=sessions)


@bp.get('/<int:session_id>')
def detail(session_id: int):
    res = get_session(user_id=g.user.id, session_id=session_id)
    if not res:
        return render_error(res, status=404)
    record = res.value
    return render_template(
        'history/detail.html',
        record=record,
        actor1=_profile_card(record.actor1_id),
        actor2=_profile_card(record.actor2_id),
    )


def _profile_card(user_id: int) -> dict[str, str | None]:
    ''' Карточка участника для просмотра. Профиль не найден — карточка остаётся пустой '''
    res = get_profile(user_id=user_id)
    if not res:
        return {'nickname': None, 'login': None}
    nickname, _avatar, login = res.value
    return {'nickname': nickname, 'login': login}
