from __future__ import annotations

from sqlalchemy import insert
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, check_punctuation, check_whitespace
from ..app import db
from ..domain import scenario as scenario_domain


def create_scenario(
        *,
        user_id: int | None = None,
        title: str | None = None,
) -> Result:
    ''' Создать пустой сценарий '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is none', severity=Severity.ERROR)
    if not title:
        title = 'new scenario'
    else:
        if not check_whitespace(value=title) or not check_punctuation(value=title):
            return Err(meta='title has whitespace or punctuation', severity=Severity.ERROR)
    try:
        with db.session.begin():
            result = db.session.execute(
                insert(scenario_domain.scenarios)
                .values(owner_id=user_id, title=title)
                .returning(scenario_domain.scenarios.c.scenario_id)
            )
            scenario_id = result.scalar_one()
        return Ok(value=scenario_id)
    except SQLAlchemyError:
        return Err(meta='db commit failed', severity=Severity.CRITICAL)
    except Exception:
        return Err(meta='db unknown error', severity=Severity.CRITICAL)


def get_scenario():
    ''' Получить сценарий '''
    return

def update_scenario():
    ''' Обновить сценарий '''
    return

def delete_scenario():
    ''' Удалить сценарий '''
    return