"""
Мозги редактора сценариев.

doc в памяти UI → мутации set_* → save().
Persistence (SQL + storage/scenarios/) — open / save / create / import_bytes.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from app.domain.models import Scenario
from app.domain.scenario import constants as C
from app.domain.scenario import roles as role_ops
from app.domain.scenario.document import coerce_document, validate_document
from app.services.result import Err, Ok, Result
from app.services.scenarios import core as scenarios_core


def create(
    user_id: int,
    *,
    title: str = "",
) -> Result[tuple[Scenario, dict[str, Any]]]:
    return scenarios_core.create_scenario(user_id, title=title)


def open_scenario(
    scenario_id: int,
    user_id: int,
) -> Result[tuple[Scenario, dict[str, Any]]]:
    return scenarios_core.load_document(scenario_id, user_id)


def save_scenario(
    scenario_id: int,
    user_id: int,
    document: dict[str, Any],
) -> Result[tuple[Scenario, dict[str, Any]]]:
    return scenarios_core.save_document(scenario_id, user_id, document)


def import_document(
    user_id: int,
    document: dict[str, Any],
    *,
    title: str | None = None,
) -> Result[tuple[Scenario, dict[str, Any]]]:
    return scenarios_core.import_from_file(user_id, document, title=title)


def parse_bytes(raw: bytes | str) -> Result[dict[str, Any]]:
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Err("invalid_json")
    data = coerce_document(data)
    if validate_document(data):
        return Err("invalid_document")
    return Ok(data)


def export_scenario(
    scenario_id: int,
    user_id: int,
) -> Result[dict[str, Any]]:
    return scenarios_core.export_document(scenario_id, user_id)


def set_title(document: dict[str, Any], title: str) -> Result[dict[str, Any]]:
    try:
        role_ops.set_scenario_title(document, title)
    except ValueError as err:
        return Err(str(err))
    return Ok(document)


def get_role(document: dict[str, Any], role_key: str) -> Result[dict[str, Any]]:
    try:
        return Ok(deepcopy(role_ops.get_role(document, role_key)))
    except ValueError as err:
        return Err(str(err))


def set_actor(
    document: dict[str, Any],
    role_key: str,
    *,
    label: str | None = None,
    goal: str | None = None,
    context: str | None = None,
    body: dict[str, Any] | None = None,
) -> Result[dict[str, Any]]:
    try:
        role_ops.set_actor_fields(
            document,
            role_key,
            label=label,
            goal=goal,
            context=context,
            body=body,
        )
    except ValueError as err:
        return Err(str(err))
    return Ok(document)


def set_actor_text(
    document: dict[str, Any],
    role_key: str,
    text: str,
) -> Result[dict[str, Any]]:
    try:
        role_ops.set_actor_body_text(document, role_key, text)
    except ValueError as err:
        return Err(str(err))
    return Ok(document)


def save_after(
    scenario_id: int,
    user_id: int,
    document: dict[str, Any],
    mutation: Result[Any],
) -> Result[tuple[Scenario, dict[str, Any]]]:
    if not mutation:
        return Err(mutation.error)
    return save_scenario(scenario_id, user_id, document)


ROLE_ACTOR1 = C.ROLE_ACTOR1
ROLE_ACTOR2 = C.ROLE_ACTOR2
ACTOR_KEYS = role_ops.ACTOR_KEYS
