"""Idempotently import the legacy SQLite data and scenario files into MySQL.

The source database is copied to a timestamped backup before any reads. The target
must be MySQL and must already be upgraded with ``flask db upgrade``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.domain.models import Scenario, User  # noqa: E402
from app.extensions import db  # noqa: E402
from app.services.auth import hash_password  # noqa: E402


def _row_dict(row):
    return {key: row[key] for key in row.keys()}


def _datetime(value):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)


def _copy_atomic(source: Path, destination: Path) -> bool:
    if destination.exists():
        if source.read_bytes() != destination.read_bytes():
            raise RuntimeError(f"Destination file differs: {destination.name}")
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".import_", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, temp_name)
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", required=True, type=Path)
    parser.add_argument("--scenario-dir", type=Path)
    parser.add_argument("--media-dir", type=Path)
    parser.add_argument("--backup-dir", type=Path, default=PROJECT_ROOT / "backups")
    args = parser.parse_args()
    source_db = args.sqlite.resolve()
    source_scenarios = (args.scenario_dir or source_db.parents[1] / "scenarios").resolve()
    source_media = (args.media_dir or source_db.parents[1] / "media").resolve()
    if not source_db.is_file():
        raise RuntimeError(f"SQLite source not found: {source_db}")

    args.backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = args.backup_dir / f"{source_db.stem}-{stamp}.db"
    shutil.copy2(source_db, backup)

    app = create_app()
    copied: list[Path] = []
    with app.app_context(), sqlite3.connect(source_db) as source:
        if db.engine.dialect.name != "mysql":
            raise RuntimeError("DATABASE_URL must point to MySQL; refusing to import")
        source.row_factory = sqlite3.Row
        user_rows = source.execute("SELECT * FROM users ORDER BY user_id").fetchall()
        scenario_rows = source.execute(
            "SELECT * FROM scenarios ORDER BY scenario_id"
        ).fetchall()
        try:
            for raw in user_rows:
                item = _row_dict(raw)
                avatar = item.get("avatar")
                if avatar:
                    relative = Path(str(avatar).replace("\\", "/"))
                    if relative.is_absolute() or ".." in relative.parts:
                        raise RuntimeError(f"Unsafe avatar path for user {item['user_id']}")
                    source_avatar = source_media / relative
                    if not source_avatar.is_file():
                        raise RuntimeError(f"Avatar file missing: {source_avatar}")
                    destination_avatar = Path(app.config["MEDIA_DIR"]) / relative
                    if _copy_atomic(source_avatar, destination_avatar):
                        copied.append(destination_avatar)
                existing = db.session.get(User, item["user_id"])
                if existing:
                    if existing.login != item["login"]:
                        raise RuntimeError(f"User ID conflict: {item['user_id']}")
                    continue
                password = item["password"]
                if not str(password).startswith(("scrypt:", "pbkdf2:")):
                    password = hash_password(str(password))
                db.session.add(
                    User(
                        user_id=item["user_id"],
                        login=item["login"],
                        password=password,
                        is_admin=bool(item.get("is_admin", 0)),
                        nickname=item.get("nickname"),
                        avatar=item.get("avatar"),
                        created_at=_datetime(item["created_at"]),
                        updated_at=_datetime(item["updated_at"]),
                        last_login_at=_datetime(item["last_login_at"]),
                    )
                )
            db.session.flush()
            target_dir = Path(app.config["SCENARIOS_DIR"])
            for raw in scenario_rows:
                item = _row_dict(raw)
                existing = db.session.get(Scenario, item["scenario_id"])
                if existing:
                    if existing.file_name != item["file_name"]:
                        raise RuntimeError(f"Scenario ID conflict: {item['scenario_id']}")
                    continue
                source_file = source_scenarios / item["file_name"]
                if not source_file.is_file():
                    raise RuntimeError(f"Scenario file missing: {source_file}")
                destination = target_dir / item["file_name"]
                if _copy_atomic(source_file, destination):
                    copied.append(destination)
                item["created_at"] = _datetime(item["created_at"])
                item["updated_at"] = _datetime(item["updated_at"])
                db.session.add(Scenario(**item))
            db.session.commit()
        except Exception:
            db.session.rollback()
            for path in copied:
                path.unlink(missing_ok=True)
            raise

        target_users = db.session.query(User).count()
        target_scenarios = db.session.query(Scenario).count()
        if target_users < len(user_rows) or target_scenarios < len(scenario_rows):
            raise RuntimeError("Post-import count verification failed")
        print(
            f"Import verified: users={len(user_rows)}, scenarios={len(scenario_rows)}, "
            f"backup={backup}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
