from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, check_punctuation, check_whitespace
from ..app import db
from ..domain import VERSION, TITLE, scenario as scenario_domain


def create_scenario(
        *,
        user_id: int | None = None,
        title: str | None = None,
) -> Result:
    ''' Создать пустой сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is none', severity=Severity.ERROR)
    if not title:
        title = TITLE
    else:
        if not check_whitespace(value=title) or not check_punctuation(value=title):
            return Err(meta='title has whitespace or punctuation', severity=Severity.ERROR)
    try:

        # транзакция

    except SQLAlchemyError:
        return Err(meta='db commit failed', severity=Severity.CRITICAL)
    except Exception:
        return Err(meta='db unknown error', severity=Severity.CRITICAL)


def get_scenario(
        *,
        user_id: int | None = None,
        scenario_id: int | None = None,
) -> Result:
    ''' Получить сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is none', severity=Severity.ERROR)
    if not scenario_id or not isinstance(scenario_id, int):
        return Err(meta='scenario_id is none', severity=Severity.ERROR)
    try:

        # транзакция

    except SQLAlchemyError:
        return Err(meta='db commit failed', severity=Severity.CRITICAL)
    except Exception:
        return Err(meta='db unknown error', severity=Severity.CRITICAL)


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
        return Err(meta='user_id is none', severity=Severity.ERROR)
    if not scenario_id or not isinstance(scenario_id, int):
        return Err(meta='scenario_id is none', severity=Severity.ERROR)
    if not patch:
        return Err(meta='patch is none', severity=Severity.ERROR)
    if not isinstance(patch, PatchScenario):
        return Err(meta='patch is not PatchScenario', severity=Severity.ERROR)
    title, version, actor1, actor2, target1, target2, context1, context2, doc1, doc2 = (
        patch.title, patch.version, patch.actor1, patch.actor2, patch.target1,
        patch.target2, patch.context1, patch.context2, patch.doc1, patch.doc2,
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
        return Ok(meta='empty patch')

    if (
        not isinstance(title, str | None)
            or (version is not None and type(version) is not int)
            or not isinstance(actor1, str | None) or not isinstance(actor2, str | None)
            or not isinstance(target1, str | None) or not isinstance(target2, str | None)
            or not isinstance(context1, str | None) or not isinstance(context2, str | None)
            or not isinstance(doc1, dict | None) or not isinstance(doc2, dict | None)
    ):
        return Err(meta='incorrect object type', severity=Severity.ERROR)
    if title is not None and not title:
        title = TITLE
    if version is not None:
        if not version:
            version = VERSION
        if version < VERSION:
            return Err(meta='old version', severity=Severity.ERROR)
        if version > VERSION:
            return Err(meta='not exist version', severity=Severity.ERROR)
    try:

        # транзакция

    except SQLAlchemyError:
        return Err(meta='db commit failed', severity=Severity.CRITICAL)
    except Exception:
        return Err(meta='db unknown error', severity=Severity.CRITICAL)


def delete_scenario(
        *,
        user_id: int | None = None,
        scenario_id: int | None = None,
) -> Result:
    ''' Удалить сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is none', severity=Severity.ERROR)
    if not scenario_id or not isinstance(scenario_id, int):
        return Err(meta='scenario_id is none', severity=Severity.ERROR)
    try:

    # транзакция

    except SQLAlchemyError:
        return Err(meta='db commit failed', severity=Severity.CRITICAL)
    except Exception:
        return Err(meta='db unknown error', severity=Severity.CRITICAL)