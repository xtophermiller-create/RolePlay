"""Create a private MySQL + user-storage backup for cron or deployment."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


def _settings() -> tuple[object, Path, Path]:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env", override=False)
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        raise RuntimeError("DATABASE_URL is not configured")
    url = make_url(raw_url)
    if not url.drivername.startswith("mysql") or not url.database:
        raise RuntimeError("DATABASE_URL must identify a MySQL database")
    scenarios = Path(os.environ.get("SCENARIOS_DIR", root / "storage" / "scenarios"))
    media = Path(os.environ.get("MEDIA_DIR", root / "storage" / "media"))
    return url, scenarios.resolve(), media.resolve()


def create_backup(destination: Path, retention_days: int) -> Path:
    url, scenarios, media = _settings()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final_path = destination / f"roleplay-trainer-{timestamp}.tar.gz"

    with tempfile.TemporaryDirectory(prefix=".backup-", dir=destination) as temp_name:
        temp = Path(temp_name)
        dump_path = temp / "database.sql"
        command = [
            "mysqldump",
            "--single-transaction",
            "--quick",
            "--default-character-set=utf8mb4",
            "--host",
            url.host or "localhost",
            "--port",
            str(url.port or 3306),
            "--user",
            url.username or "",
            url.database,
        ]
        env = os.environ.copy()
        if url.password:
            env["MYSQL_PWD"] = url.password
        try:
            with dump_path.open("wb") as dump:
                subprocess.run(
                    command,
                    stdout=dump,
                    stderr=subprocess.PIPE,
                    env=env,
                    check=True,
                    timeout=1800,
                )
        except FileNotFoundError as exc:
            raise RuntimeError("mysqldump is not installed or not on PATH") from exc
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(f"mysqldump failed: {message}") from exc

        if scenarios.is_dir():
            shutil.copytree(scenarios, temp / "scenarios")
        if (media / "avatars").is_dir():
            shutil.copytree(media / "avatars", temp / "avatars")
        (temp / "manifest.json").write_text(
            json.dumps(
                {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "database": url.database,
                    "format": 1,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary_archive = destination / f".{final_path.name}.tmp"
        with tarfile.open(temporary_archive, "w:gz") as archive:
            for item in ("database.sql", "manifest.json", "scenarios", "avatars"):
                source = temp / item
                if source.exists():
                    archive.add(source, arcname=item, recursive=True)
        temporary_archive.replace(final_path)

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    for old in destination.glob("roleplay-trainer-*.tar.gz"):
        if old == final_path:
            continue
        modified = datetime.fromtimestamp(old.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            old.unlink()
    return final_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--retention-days", type=int, default=14)
    args = parser.parse_args()
    if args.retention_days < 1:
        parser.error("--retention-days must be at least 1")
    result = create_backup(args.destination, args.retention_days)
    print(f"backup created: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
