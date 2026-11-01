from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from datetime import timedelta
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

from .service import configurate_logging, start_room_cleanup
from .web import register_pages


def create_app():
    ''' Создать Flask приложение '''
    configurate_logging()

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    web_dir = Path(__file__).resolve().parent / "web" # объявить директорию web

    app = Flask(
        __name__,
        template_folder=web_dir / "templates",
        static_folder=web_dir / "static",
    ) # объявить app с путями к директориям страниц и static

    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"] # подключиться к db
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "echo": False,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    } # настройки движка sqlalchemy через контекст app

    csrf.init_app(app)
    db.init_app(app) # инициализировать db к app
    register_pages(app) # зарегистрировать web страницы к app

    start_room_cleanup()

    return app # вернуть сам app