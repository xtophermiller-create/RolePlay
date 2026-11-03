from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from .auth import require_login

bp = Blueprint('home', __name__)
bp.before_request(require_login)


@bp.get('/')
def root():
    return redirect(url_for('home.index'))


@bp.get('/home')
def index():
    return render_template('home.html')
