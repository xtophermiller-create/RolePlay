from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, validate_fields
from ..app import db
from ..domain import Scenario


def get_scenario(
        *,
        user_id: int | None = None,
        scenario_id: int | None = None,
) -> Result[Scenario]:
    ''' Получить сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)
    if not scenario_id or not isinstance(scenario_id, int):
        return Err(meta="scenario_id is missing or invalid", severity=Severity.ERROR)

    try:
        with db.session.begin():
            scenario = db.session.execute(
                select(Scenario).where(
                    Scenario.id == scenario_id,
                    Scenario.owner_id == user_id,
                )
            ).scalar_one_or_none()
            if scenario is not None:
                db.session.expunge(scenario)

        if scenario is None:
            return Err(meta='scenario not exist', severity=Severity.INFO)
        return Ok(value=scenario)
    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)

def create_scenario(
        *,
        user_id: int | None = None,
        title: str | None = None,
) -> Result[Scenario]:
    ''' Создать пустой сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta="user_id is missing or invalid", severity=Severity.ERROR)
    res = validate_fields(scenario_title=title)
    title = res['scenario_title']['checked']
    if not title:
        return Err(meta=title.meta)
    title = res['scenario_title']['normal'].value

    try:
        with db.session.begin():
            scenario = db.session.execute(
                insert(Scenario).values(owner_id=user_id, title=title).returning(Scenario)
            ).scalar_one_or_none()
            if scenario is not None:
                db.session.expunge(scenario)

        if scenario is None:
            return Err(meta='Unknown creation error', severity=Severity.INFO)
        return Ok(value=scenario)
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
) -> Result[Scenario]:
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

    res = validate_fields(
        title=patch.title, version=patch.version, actor1=patch.actor1, actor2=patch.actor2, target1=patch.target1,
        target2=patch.target2, context1=patch.context1, context2=patch.context2, doc1=patch.doc1, doc2=patch.doc2
    )

    title = res['scenario_title']['checked']
    version = res['scenario_version']['checked']
    actor1 = res['scenario_actor1']['checked']
    actor2 = res['scenario_actor2']['checked']
    target1 = res['scenario_target1']['checked']
    target2 = res['scenario_target2']['checked']
    context1 = res['scenario_context1']['checked']
    context2 = res['scenario_context2']['checked']
    doc1 = res['scenario_doc1']['checked']
    doc2 = res['scenario_doc2']['checked']

    errors = []

    for x in [title, version, actor1, actor2, target1, target2, context1, context2, doc1, doc2]:
        if not x:
            errors.append(x.meta)

    if errors:
        errors = 'Validation error : ' + ' | '.join([error.meta for error in errors])
        return Err(meta=errors, severity=Severity.ERROR)

    title = res['scenario_title']['normal'].value
    version = res['scenario_version']['normal'].value
    actor1 = res['scenario_actor1']['normal'].value
    actor2 = res['scenario_actor2']['normal'].value
    target1 = res['scenario_target1']['normal'].value
    target2 = res['scenario_target2']['normal'].value
    context1 = res['scenario_context1']['normal'].value
    context2 = res['scenario_context2']['normal'].value
    doc1 = res['scenario_doc1']['normal'].value
    doc2 = res['scenario_doc2']['normal'].value

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

    values = {}
    if title is not None:
        values['title'] = title
    if version is not None:
        values['format_version'] = version
    if actor1 is not None:
        values['actor1'] = actor1
    if actor2 is not None:
        values['actor2'] = actor2
    if target1 is not None:
        values['target1'] = target1
    if target2 is not None:
        values['target2'] = target2
    if context1 is not None:
        values['context1'] = context1
    if context2 is not None:
        values['context2'] = context2
    if doc1 is not None:
        values['document1'] = doc1
    if doc2 is not None:
        values['document2'] = doc2

    try:
        with db.session.begin():
            scenario = db.session.execute(
                update(Scenario)
                .where(Scenario.id == scenario_id, Scenario.owner_id == user_id)
                .values(**values)
                .returning(Scenario)
            ).scalar_one_or_none()
            if scenario is not None:
                db.session.expunge(scenario)

        if scenario is None:
            return Err(meta='Unknown update error', severity=Severity.INFO)
        return Ok(value=scenario, meta='Update success')
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
        with db.session.begin():
            result = db.session.execute(
                delete(Scenario).where(
                    Scenario.id == scenario_id,
                    Scenario.owner_id == user_id,
                )
            )

        if result.rowcount == 0:
            return Err(meta='scenario not exist', severity=Severity.INFO)

        return Ok(meta='Delete success')
    except SQLAlchemyError as e:
        return Err(meta="Database transaction failed", severity=Severity.CRITICAL)
    except Exception as e:
        return Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)