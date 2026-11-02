from __future__ import annotations

from flask import g
from typing import TYPE_CHECKING
from . import auth, editor, history, home, library, profile, room
from .editor_socket import register_editor_socket
from .errors import register_errors
from .room_socket import register_room_socket
from .security import register_security

if TYPE_CHECKING:
    from flask import Flask

BLUEPRINTS = (auth.bp, home.bp, library.bp, editor.bp, profile.bp, history.bp, room.bp)


def _template_context() -> dict:
    return {'current_user': g.get('user')}


def register_web(app: Flask) -> None:
    ''' Зарегистрировать web слой '''
    app.before_request(auth.load_current_user)
    app.context_processor(_template_context)
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)

    register_room_socket()
    register_editor_socket()
    register_errors(app)
    register_security(app)


__all__ = ['register_web']
