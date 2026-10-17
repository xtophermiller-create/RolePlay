from __future__ import annotations

from flask import Blueprint, render_template, redirect, url_for
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

bp = Blueprint('pages', __name__)


@bp.get('/home')
def home():
    return render_template('home.html')

@bp.get('/editor')
def editor():
    return render_template('editor.html')

@bp.get('/library')
def library():
    return render_template('library.html')

@bp.get('/profile')
def profile():
    return render_template('profile.html')

@bp.get('/history')
def history():
    return render_template('history.html')

@bp.get('/session/new')
def create_session():
    return render_template('create_session.html')


def register_pages(app: Flask):
    ''' Зарегистрировать существующие страницы '''
    app.register_blueprint(bp) # регистрация всех страниц в bp

    @app.route('/') # страница по умолчанию
    def root():
        return redirect(url_for('pages.home'))