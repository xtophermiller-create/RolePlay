import os
import tempfile

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from app.extensions import db

bp = Blueprint("health", __name__)


def _storage_writable() -> bool:
    directories = (
        current_app.config["SCENARIOS_DIR"],
        os.path.join(current_app.config["MEDIA_DIR"], "avatars"),
    )
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        try:
            fd, probe = tempfile.mkstemp(prefix=".health-", dir=directory)
            os.close(fd)
            os.unlink(probe)
        except OSError:
            return False
    return True


@bp.get("/health/live")
def liveness():
    """Process-only probe: no database or filesystem dependencies."""
    response = jsonify(ok=True, status="live")
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/health/ready")
def readiness():
    """Dependency probe suitable for deploy smoke checks."""
    database_ok = False
    storage_ok = False
    try:
        db.session.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        current_app.logger.exception("readiness database check failed")
        db.session.remove()

    try:
        storage_ok = _storage_writable()
    except OSError:
        current_app.logger.exception("readiness storage check failed")
        storage_ok = False

    ready = database_ok and storage_ok
    payload = {
        "ok": ready,
        "status": "ready" if ready else "not_ready",
        "checks": {"database": database_ok, "storage": storage_ok},
    }
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, 200 if ready else 503


@bp.get("/health")
def health():
    """Backwards-compatible alias; readiness is the deploy-safe default."""
    return readiness()
