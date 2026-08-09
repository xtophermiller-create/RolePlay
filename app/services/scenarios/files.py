"""Чтение/запись .rpscene файлов в storage/scenarios/."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from typing import Any

from flask import current_app

from app.domain.scenario.constants import FILE_EXTENSION


def scenarios_dir() -> str:
    path = current_app.config["SCENARIOS_DIR"]
    os.makedirs(path, exist_ok=True)
    return path


def new_file_name() -> str:
    return f"{uuid.uuid4().hex}{FILE_EXTENSION}"


def absolute_path(file_name: str) -> str:
    base = os.path.basename(file_name)
    if base != file_name or ".." in file_name:
        raise ValueError("invalid scenario file_name")
    if not base.endswith(FILE_EXTENSION):
        raise ValueError("invalid scenario extension")
    return os.path.join(scenarios_dir(), base)


def write_document(file_name: str, document: dict[str, Any]) -> None:
    """Атомарная запись JSON (temp + replace)."""
    path = absolute_path(file_name)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix=".rpscene_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(document, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_document(file_name: str) -> dict[str, Any]:
    path = absolute_path(file_name)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("scenario file root must be an object")
    return data


def delete_file(file_name: str) -> None:
    path = absolute_path(file_name)
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
