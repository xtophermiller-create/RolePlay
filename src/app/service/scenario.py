from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, validate_fields
from ..domain import Scenario, SCENARIO_DEFAULT


def get_scenario(
        *,
        user_id: int | None = None,
        scenario_id: int | None = None,
) -> Result:
    ''' Получить сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)
    if not scenario_id or not isinstance(scenario_id, int):
        return Err(meta="scenario_id is missing or invalid", severity=Severity.ERROR)

    try:

        # транзакция берет сценарий по id scenario и user, нельзя выдать scenario не владельцу

    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)

def create_scenario(
        *,
        user_id: int | None = None,
        title: str | None = None,
) -> Result[int]:
    ''' Создать пустой сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)
    res = validate_fields(scenario_title=title)
    title = res['scenario_title']['checked']
    if not title:
        return Err(meta=title.meta)
    title = res['scenario_title']['normal'].value

    try:
        scenario: Scenario = None

        # транзакция создаёт сценарий с указанными title и возвращает объект db Scenario

        if scenario is None:
            return Err(meta='Unknown creation error', severity=Severity.INFO)
        return Ok(scenario)
    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)


@dataclass(frozen=True)
class PatchScenario:
    title: str | None = None
    version: int | None = None
    actor1: str | None = None
    actor2: str | None = None
    target1: str | None = None
    target2: str | None = None
    context1: str | None = None
    context2: str | None = None
    doc1: dict | None = None
    doc2: dict | None = None

def update_scenario(
        *,
        user_id: int | None = None,
        scenario_id: int | None = None,
        patch: PatchScenario | None = None,
) -> Result:
    ''' Обновить сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)
    if not scenario_id or not isinstance(scenario_id, int):
        return Err(meta="scenario_id is missing or invalid", severity=Severity.ERROR)
    if not patch:
        return Err(meta="patch is missing", severity=Severity.ERROR)
    if not isinstance(patch, PatchScenario):
        return Err(meta="patch must be a PatchScenario instance", severity=Severity.ERROR)
    if patch is None or not patch:
        return Err(meta="patch is missing", severity=Severity.ERROR)

    title, version, actor1, actor2, target1, target2, context1, context2, doc1, doc2 = (
        patch.title, patch.version, patch.actor1, patch.actor2, patch.target1,
        patch.target2, patch.context1, patch.context2, patch.doc1, patch.doc2,
    )

    res = validate_fields(
        title=title, version=version, actor1=actor1, actor2=actor2, target1=target1, target2=target2, context1=context1,
        context2=context2, doc1=doc1, doc2=doc2
    )

    if all(
        value is None for value in (
            title, version,
            actor1, actor2,
            target1, target2,
            context1, context2,
            doc1, doc2
        )
    ):
        return Ok(meta="No fields to update")

    if (
        not isinstance(title, str | None)
            or (version is not None and type(version) is not int)
            or not isinstance(actor1, str | None) or not isinstance(actor2, str | None)
            or not isinstance(target1, str | None) or not isinstance(target2, str | None)
            or not isinstance(context1, str | None) or not isinstance(context2, str | None)
            or not isinstance(doc1, dict | None) or not isinstance(doc2, dict | None)
    ):
        return Err(meta="One or more fields have invalid types", severity=Severity.ERROR)

    if title is not None and not title:
        title = SCENARIO_TITLE
    if version is not None:
        if not version:
            version = SCENARIO_VERSION
        if version < SCENARIO_VERSION:
            return Err(meta="Scenario version is outdated", severity=Severity.ERROR)
        if version > SCENARIO_VERSION:
            return Err(meta="Scenario version is not supported", severity=Severity.ERROR)

    for length, field, field_name in zip(
        [LENGTH_TITLE, LENGTH_ACTOR1, LENGTH_ACTOR2, LENGTH_TARGET1,LENGTH_TARGET2, LENGTH_CONTEXT1, LENGTH_CONTEXT2],
        [title, actor1, actor2, target1, target2, context1, context2],
        ['title', 'actor1', 'actor2', 'target1', 'target2', 'context1', 'context2'],
    ):
        if isinstance(field, str):
            if len(field.strip()) > length:
                return Err(meta=f"{field_name} exceeds maximum length", severity=Severity.ERROR)

    try:

        # транзакция

    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)


def delete_scenario(
        *,
        user_id: int | None = None,
        scenario_id: int | None = None,
) -> Result:
    ''' Удалить сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)
    if not scenario_id or not isinstance(scenario_id, int):
        return Err(meta="scenario_id is missing or invalid", severity=Severity.ERROR)

    try:

    # транзакция

    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)