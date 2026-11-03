from __future__ import annotations

from flask import render_template
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

HTTP_MESSAGES = {
    400: 'Некорректный запрос',
    403: 'Доступ запрещён',
    404: 'Страница не найдена',
    405: 'Метод не поддерживается',
    413: 'Слишком большой запрос',
    429: 'Слишком много запросов, попробуйте позже',
    500: 'Что-то пошло не так',
}
CSRF_MESSAGE = 'Форма устарела, обновите страницу и попробуйте снова'


def _http_error(e: HTTPException):
    message = HTTP_MESSAGES.get(e.code, HTTP_MESSAGES[500])
    return render_template('error.html', code=e.code, message=message), e.code


def _csrf_error(e: CSRFError):
    return render_template('error.html', code=400, message=CSRF_MESSAGE), 400


def register_errors(app: Flask) -> None:
    ''' Свои страницы ошибок без деталей исключений; необработанное исключение приходит как 500 '''
    app.register_error_handler(CSRFError, _csrf_error)
    app.register_error_handler(HTTPException, _http_error)
