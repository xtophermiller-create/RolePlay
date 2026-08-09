"""CRUD сценариев: SQL-метаданные + файл документа в storage/scenarios/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.domain.models import Scenario, User
from app.domain.scenario.constants import FORMAT_VERSION
from app.domain.scenario.document import (
    document_title,
    empty_document,
    validate_document,
)
from app.extensions import db
from app.services.commit import try_commit
from app.services.result import Err, Ok, Result
from app.services.scenarios import files as scenario_files


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_scenario(scenario_id: int, user_id: int | None = None) -> Scenario | None:
    q = Scenario.query.filter_by(scenario_id=scenario_id)
    if user_id is not None:
        q = q.filter_by(owner_user_id=user_id)
    return q.first()


def list_scenarios(user_id: int) -> list[Scenario]:
    return (
        Scenario.query.filter_by(owner_user_id=user_id)
        .order_by(Scenario.updated_at.desc())
        .all()
    )


def create_scenario(
    user_id: int,
    *,
    title: str = "",
    document: dict[str, Any] | None = None,
) -> Result[tuple[Scenario, dict[str, Any]]]:
    """Создать пустой или из готового документа. Пишет файл + строку в SQL."""
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return Err("user_not_found")

    if document is None:
        doc = empty_document(title=title)
    else:
        doc = document
        if title:
            doc["title"] = title.strip()

    if validate_document(doc):
        return Err("invalid_document")

    file_name = scenario_files.new_file_name()
    try:
        scenario_files.write_document(file_name, doc)
    except OSError:
        return Err("file_write_failed")

    row = Scenario(
        owner_user_id=user_id,
        title=document_title(doc) or (title or "").strip() or "Без названия",
        file_name=file_name,
        format_version=int(doc.get("version") or FORMAT_VERSION),
    )
    db.session.add(row)
    if not try_commit():
        scenario_files.delete_file(file_name)
        return Err("db_commit_failed")

    return Ok((row, doc))


def load_document(scenario_id: int, user_id: int) -> Result[tuple[Scenario, dict[str, Any]]]:
    row = get_scenario(scenario_id, user_id)
    if not row:
        return Err("not_found")
    try:
        doc = scenario_files.read_document(row.file_name)
    except FileNotFoundError:
        return Err("file_missing")
    except (OSError, ValueError, json.JSONDecodeError):
        return Err("file_read_failed")
    return Ok((row, doc))


def save_document(
    scenario_id: int,
    user_id: int,
    document: dict[str, Any],
) -> Result[tuple[Scenario, dict[str, Any]]]:
    """Перезаписать тело сценария и синхронизировать title/version в SQL."""
    row = get_scenario(scenario_id, user_id)
    if not row:
        return Err("not_found")

    if validate_document(document):
        return Err("invalid_document")

    try:
        scenario_files.write_document(row.file_name, document)
    except OSError:
        return Err("file_write_failed")

    row.title = document_title(document) or row.title or "Без названия"
    row.format_version = int(document.get("version") or FORMAT_VERSION)
    row.updated_at = _utcnow()
    if not try_commit():
        return Err("db_commit_failed")

    return Ok((row, document))


def import_from_file(
    user_id: int,
    document: dict[str, Any],
    *,
    title: str | None = None,
) -> Result[tuple[Scenario, dict[str, Any]]]:
    return create_scenario(user_id, title=title or "", document=document)


def export_document(scenario_id: int, user_id: int) -> Result[dict[str, Any]]:
    result = load_document(scenario_id, user_id)
    if not result:
        return Err(result.error)
    return Ok(result.value[1])


def delete_scenario(scenario_id: int, user_id: int) -> Result[bool]:
    row = get_scenario(scenario_id, user_id)
    if not row:
        return Err("not_found")

    file_name = row.file_name
    db.session.delete(row)
    if not try_commit():
        return Err("db_commit_failed")

    scenario_files.delete_file(file_name)
    return Ok(True)
