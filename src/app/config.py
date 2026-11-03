from __future__ import annotations

import os
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

TRUE_VALUES = frozenset({'1', 'true', 'yes', 'on'})
FORM_SIZE_LIMIT = 1024 * 1024  # 1 МБ на обычные формы


def env_flag(name: str, *, default: bool = False) -> bool:
    ''' Прочитать булев флаг из окружения '''
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def configure(app: Flask) -> None:
    ''' Заполнить конфигурацию приложения из окружения '''
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

    # локально по http:// выключить, иначе браузер не отправит cookie
    app.config["SESSION_COOKIE_SECURE"] = env_flag("SESSION_COOKIE_SECURE", default=True)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=3)

    app.config["MAX_CONTENT_LENGTH"] = FORM_SIZE_LIMIT
    app.config["MAX_FORM_MEMORY_SIZE"] = FORM_SIZE_LIMIT
    app.config["MAX_FORM_PARTS"] = 100

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"] # подключиться к db
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "echo": False,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "hide_parameters": True
    } # настройки движка sqlalchemy через контекст app
