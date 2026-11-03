from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
csrf = CSRFProtect()
# хранилище в памяти допустимо: процесс строго один
limiter = Limiter(get_remote_address, storage_uri="memory://")
# threading: валидатор вызывает asyncio.run, с eventlet/gevent это конфликтует.
# cors_allowed_origins не задан: по умолчанию разрешён только свой origin
socketio = SocketIO(async_mode="threading")

from .config import configure, env_flag
from .service import configurate_logging, start_room_cleanup, start_draft_cleanup
from .web import register_web


def create_app():
    ''' Создать Flask приложение. Вызывать ровно один раз на процесс: запускает поток очистки комнат '''
    configurate_logging()

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    web_dir = Path(__file__).resolve().parent / "web" # объявить директорию web

    app = Flask(
        __name__,
        template_folder=web_dir / "templates",
        static_folder=web_dir / "static",
    ) # объявить app с путями к директориям страниц и static

    configure(app)

    csrf.init_app(app)
    db.init_app(app) # инициализировать db к app
    limiter.init_app(app)
    socketio.init_app(app)
    register_web(app) # зарегистрировать web слой к app

    # после socketio, чтобы ProxyFix был внешним слоем и для HTTP, и для WebSocket.
    # только за nginx: без прокси заголовки X-Forwarded-* может подделать любой клиент
    if env_flag("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    start_draft_cleanup()
    start_room_cleanup()

    return app # вернуть сам app
