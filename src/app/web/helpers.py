from __future__ import annotations

import logging
from flask import abort, render_template, request
from ..service.helper import Err, Severity

logger = logging.getLogger(__name__)

GENERIC_ERROR = 'Что-то пошло не так'
LOGGED_SEVERITIES = frozenset({Severity.ERROR, Severity.CRITICAL})


def err_message(err: Err) -> str:
    ''' Текст ошибки service для пользователя; серьёзные ошибки дополнительно пишутся в лог '''
    if err.severity in LOGGED_SEVERITIES:
        logger.error('%s %s: %s', request.method, request.path, err.meta)
    return err.meta or GENERIC_ERROR


def err_status(err: Err, *, default: int = 400) -> int:
    ''' HTTP статус для ошибки service '''
    if err.severity is Severity.CRITICAL:
        return 500
    return default


def render_error(err: Err, *, status: int = 400):
    ''' Отдельная страница ошибки service '''
    return render_template('error.html', message=err_message(err)), err_status(err, default=status)


def form_int(name: str) -> int:
    ''' Целое из формы; иначе 400 '''
    try:
        return int(request.form[name])
    except (KeyError, ValueError):
        abort(400)
