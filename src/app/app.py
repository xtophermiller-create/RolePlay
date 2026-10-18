from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from .domain import init_scenarios, init_rooms, init_users, init_sessions
from .web import register_pages

db = SQLAlchemy() # объявить db


def create_app():
    ''' Создать Flask приложение '''
    load_dotenv(Path(__file__).resolve().parents[2] / ".env") # объявить путь к .env? не понимаю dotenv
    web_dir = Path(__file__).resolve().parent / "web" # объявить директорию web
    app = Flask(
        __name__,
        template_folder=web_dir / "templates",
        static_folder=web_dir / "static",
    ) # объявить app с путями к директориям страниц и static
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"] # подключиться к db
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "echo": True,
        "pool_size": 5,
        "max_overflow": 10,
    } # настройки движка sqlalchemy через контекст app
    db.init_app(app) # инициализировать db к app
    with app.app_context(): # инициализируем tables в db, для ORM
        init_scenarios(db.engine)
        init_rooms(db.engine)
        init_users(db.engine)
        init_sessions(db.engine)
    register_pages(app) # зарегистрировать web страницы к app
    return app # вернуть сам app