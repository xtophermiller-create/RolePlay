from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, session, url_for
from ..service.profile import PatchProfile, get_profile, update_profile
from .auth import CurrentUser, _remember, require_login
from .helpers import err_message, err_status

bp = Blueprint('profile', __name__, url_prefix='/profile')
bp.before_request(require_login)


@bp.route('', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('profile.html', nickname=g.user.nickname, login=g.user.login)

    # avatar не принимаем из формы: имя файла будет выдавать сервер при загрузке
    nickname = request.form.get('nickname')
    res = update_profile(user_id=g.user.id, patch=PatchProfile(nickname=nickname))
    if not res:
        return render_template(
            'profile.html',
            nickname=nickname,
            login=g.user.login,
            errors=[err_message(res)],
        ), err_status(res)

    fresh = get_profile(user_id=g.user.id)
    if fresh:
        fresh_nickname, avatar, login = fresh.value
        _remember(CurrentUser(id=g.user.id, nickname=fresh_nickname, avatar=avatar, login=login))
    else:
        session.pop('profile', None)
    return redirect(url_for('profile.index'))
