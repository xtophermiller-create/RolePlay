"""Environment-driven application configuration."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        raise RuntimeError(f"{name} must be an integer") from None


def load_config(base_dir: str) -> dict:
    base = Path(base_dir)
    environment = os.getenv("APP_ENV", "development").strip().lower()
    production = environment == "production"
    secret = os.getenv("SECRET_KEY", "").strip()
    if production and (not secret or secret == "dev-change-me" or len(secret) < 32):
        raise RuntimeError("Production requires a non-default SECRET_KEY of at least 32 characters")
    if not secret:
        secret = "dev-change-me"

    sqlite_path = (base / "storage" / "db" / "roleplay_trainer.db").resolve()
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{sqlite_path.as_posix()}").strip()
    if database_url.startswith("mysql://"):
        database_url = "mysql+pymysql://" + database_url[len("mysql://") :]

    secure_cookies = _bool("SESSION_COOKIE_SECURE", production)
    registration_mode = os.getenv(
        "REGISTRATION_MODE", "closed" if production else "open"
    ).strip().lower()
    turnstile_default = production and registration_mode != "closed"
    turnstile_required = _bool("TURNSTILE_REQUIRED", turnstile_default)
    return {
        "APP_ENV": environment,
        "SECRET_KEY": secret,
        "SQLALCHEMY_DATABASE_URI": database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "pool_recycle": 280},
        "SCENARIOS_DIR": os.getenv(
            "SCENARIOS_DIR", str((base / "storage" / "scenarios").resolve())
        ),
        "MEDIA_DIR": os.getenv("MEDIA_DIR", str((base / "storage" / "media").resolve())),
        "MAX_CONTENT_LENGTH": _int("MAX_REQUEST_BYTES", 2 * 1024 * 1024, 1024),
        "MAX_JSON_BYTES": _int("MAX_JSON_BYTES", 1024 * 1024, 1024),
        "MAX_AVATAR_BYTES": _int("MAX_AVATAR_BYTES", 2 * 1024 * 1024, 1024),
        "MAX_AVATAR_PIXELS": _int("MAX_AVATAR_PIXELS", 16_000_000, 1),
        "MAX_AVATAR_DIMENSION": _int("MAX_AVATAR_DIMENSION", 8192, 1),
        "MAX_SCENARIO_BYTES": _int("MAX_SCENARIO_BYTES", 1024 * 1024, 1024),
        "SESSION_COOKIE_SECURE": secure_cookies,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": timedelta(
            seconds=_int("SESSION_TTL_SECONDS", 8 * 60 * 60, 300)
        ),
        "TRUSTED_PROXY_COUNT": _int("TRUSTED_PROXY_COUNT", 0),
        "TRUSTED_HOSTS": [
            host.strip()
            for host in os.getenv("TRUSTED_HOSTS", "").split(",")
            if host.strip()
        ],
        "REGISTRATION_MODE": registration_mode,
        "REGISTRATION_INVITE_CODE": os.getenv("REGISTRATION_INVITE_CODE", ""),
        "TURNSTILE_SITE_KEY": os.getenv("TURNSTILE_SITE_KEY", ""),
        "TURNSTILE_SECRET_KEY": os.getenv("TURNSTILE_SECRET_KEY", ""),
        "TURNSTILE_REQUIRED": turnstile_required,
        "AUTH_WINDOW_SECONDS": _int("AUTH_WINDOW_SECONDS", 900, 60),
        "AUTH_MAX_FAILURES": _int("AUTH_MAX_FAILURES", 5, 1),
        "AUTH_BLOCK_SECONDS": _int("AUTH_BLOCK_SECONDS", 900, 1),
        "SESSION_INVITE_TTL_SECONDS": _int("SESSION_INVITE_TTL_SECONDS", 30, 5),
        # Лобби: нет ping дольше этого → гость вылетает, хост отменяет сессию.
        "SESSION_PRESENCE_TIMEOUT_SECONDS": _int(
            "SESSION_PRESENCE_TIMEOUT_SECONDS", 60, 15
        ),
        # Active бой: только явный away (закрытие вкладки), не «пропущенный ping».
        "SESSION_PRESENCE_ACTIVE_TIMEOUT_SECONDS": _int(
            "SESSION_PRESENCE_ACTIVE_TIMEOUT_SECONDS", 90, 30
        ),
        # Гостевые аккаунты живут от created_at; потом удаляются.
        "GUEST_TTL_SECONDS": _int("GUEST_TTL_SECONDS", 24 * 60 * 60, 60),
        "HSTS_ENABLED": _bool("HSTS_ENABLED", production),
    }
