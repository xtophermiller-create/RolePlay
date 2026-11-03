from __future__ import annotations

from dataclasses import dataclass
from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for
from ..app import limiter
from ..service.helper import Severity
from ..service.profile import get_profile
from ..service.user import authenticate, create_user
from .helpers import err_message, err_status
from .security import is_safe_path

bp = Blueprint('auth', __name__)

LOGIN_LIMIT = '10 per minute'
REGISTER_LIMIT = '5 per minute'


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: int
    nickname: str | None
    avatar: str | None
    login: str


def _remember(user: CurrentUser) -> None:
    ''' Положить профиль в подписанную cookie: страница больше не спрашивает его у базы '''
    session['profile'] = {
        'nickname': user.nickname,
        'avatar': user.avatar,
        'login': user.login,
    }


def _cached_user(user_id: int) -> CurrentUser | None:
    profile = session.get('profile')
    if not isinstance(profile, dict):
        return None
    login = profile.get('login')
    nickname = profile.get('nickname')
    avatar = profile.get('avatar')
    if not isinstance(login, str) or not login:
        return None
    if nickname is not None and not isinstance(nickname, str):
        return None
    if avatar is not None and not isinstance(avatar, str):
        return None
    return CurrentUser(id=user_id, nickname=nickname, avatar=avatar, login=login)


def load_current_user() -> None:
    ''' Загрузить пользователя сессии в g.user; удалённого пользователя разлогинить '''
    g.user = None
    user_id = session.get('user_id')
    if user_id is None or request.endpoint == 'static':
        return
    if type(user_id) is not int:
        session.clear()
        return

    cached = _cached_user(user_id)
    if cached is not None:
        g.user = cached
        return

    res = get_profile(user_id=user_id)
    if res:
        nickname, avatar, login = res.value
        g.user = CurrentUser(id=user_id, nickname=nickname, avatar=avatar, login=login)
        _remember(g.user)
        return
    if res.severity is Severity.INFO:
        session.clear()
        return
    err_message(res)
    abort(500)


def require_login():
    ''' before_request для закрытых blueprint '''
    if g.user is not None:
        return None
    if request.method == 'GET':
        return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))
    return redirect(url_for('auth.login'))


def _start_session(user_id: int):
    ''' Новая сессия после входа: защита от фиксации сессии '''
    session.clear()
    session['user_id'] = user_id
    session.permanent = True


def _next_url() -> str:
    target = request.values.get('next')
    return target if is_safe_path(target) else url_for('home.index')


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit(LOGIN_LIMIT, methods=['POST'])
def login():
    if g.user is not None:
        return redirect(url_for('home.index'))
    if request.method == 'GET':
        return render_template('auth/login.html', next=request.args.get('next'))

    login_value = request.form.get('login')
    res = authenticate(login=login_value, password=request.form.get('password'))
    if not res:
        return render_template(
            'auth/login.html',
            errors=[err_message(res)], login=login_value, next=request.form.get('next'),
        ), err_status(res)

    user_id, login_name, nickname, avatar, *_ = res.value
    _start_session(user_id)
    _remember(CurrentUser(id=user_id, nickname=nickname, avatar=avatar, login=login_name))
    return redirect(_next_url())


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit(REGISTER_LIMIT, methods=['POST'])
def register():
    if g.user is not None:
        return redirect(url_for('home.index'))
    if request.method == 'GET':
        return render_template('auth/register.html')

    login_value = request.form.get('login')
    res = create_user(login=login_value, password=request.form.get('password'))
    if not res:
        return render_template(
            'auth/register.html', errors=[err_message(res)], login=login_value,
        ), err_status(res)

    user_id, login_name, nickname, avatar, *_ = res.value
    _start_session(user_id)
    _remember(CurrentUser(id=user_id, nickname=nickname, avatar=avatar, login=login_name))
    return redirect(url_for('home.index'))


@bp.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
