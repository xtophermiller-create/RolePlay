from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
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
    db.init_app(app) # инициализировать db к app
    register_pages(app) # зарегистрировать web страницы к app
    return app # вернуть сам app