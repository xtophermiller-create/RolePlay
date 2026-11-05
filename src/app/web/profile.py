from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, session, url_for
from ..service.profile import PatchProfile, get_profile, update_profile
from ..service.user import change_login, change_password
from .auth import CurrentUser, _remember, require_login
from .helpers import err_message, err_status

bp = Blueprint('profile', __name__, url_prefix='/profile')
bp.before_request(require_login)


def _remember_profile() -> None:
    ''' Обновить логин в сессии после смены, чтобы страница не показывала старый '''
    fresh = get_profile(user_id=g.user.id)
    if fresh:
        nickname, avatar, login = fresh.value
        _remember(CurrentUser(id=g.user.id, nickname=nickname, avatar=avatar, login=login))
    else:
        session.pop('profile', None)


def _render(*, nickname, errors=None, status=200, open_popup=None, login_draft=''):
    rendered = render_template(
        'profile.html',
        nickname=nickname,
        login=g.user.login,
        errors=errors,
        open_popup=open_popup,
        login_draft=login_draft,
    )
    if status == 200:
        return rendered
    return rendered, status


@bp.route('', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return _render(nickname=g.user.nickname)

    # avatar не принимаем из формы: имя файла будет выдавать сервер при загрузке
    nickname = request.form.get('nickname')
    res = update_profile(user_id=g.user.id, patch=PatchProfile(nickname=nickname))
    if not res:
        return _render(nickname=nickname, errors=[err_message(res)], status=err_status(res))

    _remember_profile()
    return redirect(url_for('profile.index'))


@bp.get('/login')
@bp.get('/password')
def account_get():
    return redirect(url_for('profile.index'))


@bp.post('/login')
def login():
    new_login = request.form.get('new_login')
    res = change_login(user_id=g.user.id, password=request.form.get('password'), new_login=new_login)
    if not res:
        return _render(
            nickname=g.user.nickname,
            errors=[err_message(res)],
            status=err_status(res),
            open_popup='login',
            login_draft=new_login or '',
        )

    _remember_profile()
    return redirect(url_for('profile.index'))


@bp.post('/password')
def password():
    res = change_password(
        user_id=g.user.id,
        old_password=request.form.get('old_password'),
        new_password=request.form.get('new_password'),
    )
    if not res:
        return _render(
            nickname=g.user.nickname,
            errors=[err_message(res)],
            status=err_status(res),
            open_popup='password',
        )
    return redirect(url_for('profile.index'))
