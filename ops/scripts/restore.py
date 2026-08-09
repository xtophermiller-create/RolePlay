"""Explicit production restore with a mandatory safety backup."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backup import _settings, create_backup


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (root / member.name).resolve()
        if root not in target.parents and target != root:
            raise RuntimeError(f"unsafe path in archive: {member.name}")
        if member.issym() or member.islnk() or member.isdev():
            raise RuntimeError(f"links/devices are not allowed in backup: {member.name}")
    archive.extractall(root)


def _replace_directory(source: Path, target: Path, suffix: str) -> Path:
    staged = target.parent / f".restore-{target.name}-{suffix}"
    previous = target.parent / f".pre-restore-{target.name}-{suffix}"
    if staged.exists() or previous.exists():
        raise RuntimeError("restore staging path already exists")
    shutil.copytree(source, staged)
    if target.exists():
        os.replace(target, previous)
    os.replace(staged, target)
    return previous


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--safety-backup-destination", type=Path)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "RESTORE-PRODUCTION":
        parser.error("--confirm must be exactly RESTORE-PRODUCTION")
    archive_path = args.archive.resolve()
    if not archive_path.is_file():
        parser.error(f"archive does not exist: {archive_path}")

    url, scenarios, media = _settings()
    backup_destination = (
        args.safety_backup_destination or archive_path.parent
    ).resolve()
    safety = create_backup(backup_destination, retention_days=14)
    print(f"pre-restore safety backup: {safety}")

    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory(prefix=".restore-", dir=backup_destination) as temp_name:
        temp = Path(temp_name)
        with tarfile.open(archive_path, "r:gz") as archive:
            _safe_extract(archive, temp)
        required = (temp / "database.sql", temp / "scenarios", temp / "avatars")
        if not all(item.exists() for item in required):
            raise RuntimeError("backup is incomplete: database.sql/scenarios/avatars required")

        command = [
            "mysql",
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
            with (temp / "database.sql").open("rb") as dump:
                subprocess.run(
                    command,
                    stdin=dump,
                    stderr=subprocess.PIPE,
                    env=env,
                    check=True,
                    timeout=1800,
                )
        except FileNotFoundError as exc:
            raise RuntimeError("mysql client is not installed or not on PATH") from exc
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(f"mysql restore failed: {message}") from exc

        old_scenarios = _replace_directory(temp / "scenarios", scenarios, suffix)
        old_avatars = _replace_directory(temp / "avatars", media / "avatars", suffix)
        print(f"restore complete; previous files retained at {old_scenarios} and {old_avatars}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
