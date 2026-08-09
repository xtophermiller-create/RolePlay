"""Подсчёт итога сессии.

Оценочные fields/scoring выпилены из domain.scenario — заглушка под старый API.
"""

from __future__ import annotations

from typing import Any

from app.services.result import Err, Result


def score_session(
    scenario_document: dict[str, Any],
    values: dict[str, Any] | None = None,
) -> Result[dict[str, Any]]:
    del scenario_document, values
    return Err("not_implemented")


def score_fields(
    fields: list[dict[str, Any]],
    values: dict[str, Any] | None = None,
) -> Result[dict[str, Any]]:
    del fields, values
    return Err("not_implemented")
