from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import SQLAlchemyError
from .helper import Result, Err, Ok, Severity, validate_fields, txn
from ..domain import Scenario


def get_scenario(
        *,
        user_id: int | None = None,
        scenario_id: int | None = None,
) -> Result[Scenario]:
    ''' Получить сценарий как объект Scenario '''
    # проверка user_id на тип int
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)
    # проверка scenario_id на тип int
    if type(scenario_id) is not int:
        return Err(meta="scenario_id is not int", severity=Severity.ERROR)

    # начало транзакции заключаем в try
    try:
        with txn() as s:
            scenario = s.execute(
                select(Scenario).where(Scenario.id == scenario_id, Scenario.owner_id == user_id)
            ).scalar_one_or_none()

            # отсоединяем scenario от сессии
            if scenario is not None:
                s.expunge(scenario)

        if scenario is None:
            return Err(meta="Scenario not found", severity=Severity.ERROR)

        return Ok(value=scenario)

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


def get_scenarios(
        *,
        user_id: int | None = None,
) -> Result[list[Scenario] | str]:
    ''' Возвращает все сценарии владельца по user_id '''
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)

    # заключаем транзакцию в try
    try:
        with txn() as s:
            raw_scenarios = s.execute(
                select(Scenario).where(Scenario.owner_id == user_id)
            ).scalars().all()

            scenarios = []

            for scenario in raw_scenarios:
                if scenario is not None:
                    s.expunge(scenario)
                    scenarios.append(scenario)

        if not scenarios:
            return Ok(meta='Scenarios not found')

        return Ok(value=scenarios)

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


def create_scenario(
        *,
        user_id: int | None = None,
        title: str | None = None,
) -> Result[Scenario]:
    ''' Создать пустой сценарий (с title) '''
    # проверка user_id на тип int
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)

    # отправляем title на валидацию и обрабатываем результат
    res = validate_fields(scenario_title=title)
    res_title = res['scenario_title']['checked']
    if not res_title:
        return Err(meta=f'Validation errors: {res_title.meta}')
    title = res['scenario_title']['normal'].value

    # заключаем транзакцию в try
    try:
        with txn() as s:
            scenario = s.execute(
                insert(Scenario).values(owner_id=user_id, title=title).returning(Scenario)
            ).scalar_one_or_none()

            if scenario is not None:
                s.expunge(scenario)

        if scenario is None:
            return Err(meta='Scenario not found', severity=Severity.INFO)

        return Ok(value=scenario)

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


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
    # проверяем user_id на тип int
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)
    # проверяем scenario_id на тип int
    if type(scenario_id) is not int:
        return Err(meta="scenario_id is not int", severity=Severity.ERROR)
    # проверяем patch на тип PatchScenario
    if type(patch) is not PatchScenario:
        return Err(meta="patch is not PatchScenario", severity=Severity.ERROR)

    # отправляем patch fields на валидацию и обрабатываем результат
    res = validate_fields(
        scenario_title=patch.title, scenario_version=patch.version, scenario_actor1=patch.actor1,
        scenario_actor2=patch.actor2, scenario_target1=patch.target1, scenario_target2=patch.target2,
        scenario_context1=patch.context1, scenario_context2=patch.context2, scenario_doc1=patch.doc1,
        scenario_doc2=patch.doc2
    )

    res_title = res['scenario_title']['checked']
    res_version = res['scenario_version']['checked']
    res_actor1 = res['scenario_actor1']['checked']
    res_actor2 = res['scenario_actor2']['checked']
    res_target1 = res['scenario_target1']['checked']
    res_target2 = res['scenario_target2']['checked']
    res_context1 = res['scenario_context1']['checked']
    res_context2 = res['scenario_context2']['checked']
    res_doc1 = res['scenario_doc1']['checked']
    res_doc2 = res['scenario_doc2']['checked']

    errors = []

    for x in [
        res_title, res_version, res_actor1, res_actor2, res_target1,
        res_target2, res_context1, res_context2, res_doc1, res_doc2
    ]:
        if not x:
            errors.append(x.meta)

    if errors:
        errors = 'Validation error: ' + ' | '.join(errors)
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

    # если все поля None - значит ничего менять не нужно, это не ошибка
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

    # соединяем fields которые not None
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

    # заключаем транзакцию в try
    try:
        with txn() as s:
            scenario = s.execute(
                update(Scenario)
                .where(Scenario.id == scenario_id, Scenario.owner_id == user_id)
                .values(**values)
                .returning(Scenario)
            ).scalar_one_or_none()

            if scenario is not None:
                s.expunge(scenario)

        if scenario is None:
            return Err(meta='scenario not found', severity=Severity.INFO)

        return Ok(value=scenario, meta='Update success')

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


def delete_scenario(
        *,
        user_id: int | None = None,
        scenario_id: int | None = None,
) -> Result:
    ''' Удалить сценарий '''
    # проверяем user_id на тип int
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)
    # проверяем scenario_id на тип int
    if type(scenario_id) is not int:
        return Err(meta="scenario_id is not int", severity=Severity.ERROR)

    # заключаем транзакцию в try
    try:
        with txn() as s:
            res = s.execute(
                delete(Scenario).where(Scenario.id == scenario_id, Scenario.owner_id == user_id)
            )

        if res.rowcount == 0:
            return Err(meta='Scenario not found', severity=Severity.INFO)

        return Ok()

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)