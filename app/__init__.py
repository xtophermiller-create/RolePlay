import os

from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import load_config
from app.extensions import csrf, db, migrate
from app.observability import configure_logging
from app.security import install_request_security

_SQLITE_PRAGMA_LISTENER = False


def _sqlite_on_connect(dbapi_conn, _connection_record):
    """WAL + FK на каждое новое sqlite3-соединение."""
    if dbapi_conn.__class__.__module__ != "sqlite3":
        return
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _should_auto_migrate(app: Flask) -> bool:
    """Авто-migrate: dev по умолчанию; prod только с явным флагом."""
    flag = os.environ.get("ROLEPLAY_TRAINER_AUTO_MIGRATE", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    return app.config.get("APP_ENV", "development") != "production"


def create_app():
    global _SQLITE_PRAGMA_LISTENER

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(os.path.join(base_dir, ".env"), override=False)
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "web", "templates"),
        static_folder=os.path.join(base_dir, "web", "static"),
    )

    app.config.update(load_config(base_dir))
    configure_logging(app)
    os.makedirs(app.config["SCENARIOS_DIR"], exist_ok=True)
    os.makedirs(os.path.join(app.config["MEDIA_DIR"], "avatars"), exist_ok=True)
    os.makedirs(os.path.join(app.config["MEDIA_DIR"], "scenarios"), exist_ok=True)
    proxy_count = app.config["TRUSTED_PROXY_COUNT"]
    if proxy_count:
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=proxy_count, x_proto=proxy_count, x_host=proxy_count
        )

    dev_hot = os.environ.get("ROLEPLAY_TRAINER_DEV", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    app.config["TEMPLATES_AUTO_RELOAD"] = dev_hot
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0 if dev_hot else 3600
    app.jinja_env.auto_reload = dev_hot

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    install_request_security(app)

    if not _SQLITE_PRAGMA_LISTENER:
        event.listen(Engine, "connect", _sqlite_on_connect)
        _SQLITE_PRAGMA_LISTENER = True

    from app.domain import models as _domain_models  # noqa: F401
    from web.bootstrap import register_app_shell
    from web.routes import auth, health, home, profile, scenarios, sessions

    app.register_blueprint(auth.bp)
    app.register_blueprint(home.bp)
    app.register_blueprint(profile.bp)
    app.register_blueprint(scenarios.bp)
    app.register_blueprint(sessions.bp)
    app.register_blueprint(health.bp)
    register_app_shell(app)

    if _should_auto_migrate(app):
        with app.app_context():
            from flask_migrate import upgrade as alembic_upgrade

            alembic_upgrade(directory=os.path.join(base_dir, "migrations"))

    return app
