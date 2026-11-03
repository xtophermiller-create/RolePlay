from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, url_for
from ..service.profile import PatchProfile, update_profile
from .auth import require_login
from .helpers import err_message, err_status

bp = Blueprint('profile', __name__, url_prefix='/profile')
bp.before_request(require_login)


@bp.route('', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('profile.html', nickname=g.user.nickname)

    # avatar не принимаем из формы: имя файла будет выдавать сервер при загрузке
    nickname = request.form.get('nickname')
    res = update_profile(user_id=g.user.id, patch=PatchProfile(nickname=nickname))
    if not res:
        return render_template(
            'profile.html', nickname=nickname, errors=[err_message(res)],
        ), err_status(res)
    return redirect(url_for('profile.index'))
