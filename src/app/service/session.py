from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError

from .helper import Result, Err, Ok, Severity, validate_fields, txn
from ..domain import Session, SessionObserver


@dataclass(frozen=True)
class PatchSession:
    owner_id: int | None = None
    actor1_id: int | None = None
    actor2_id: int | None = None
    observer_ids: list[int] | None = None
    title: str | None = None
    format_version: int | None = None
    actor1: str | None = None
    actor2: str | None = None
    target1: str | None = None
    target2: str | None = None
    context1: str | None = None
    context2: str | None = None
    doc1: dict | None = None
    doc2: dict | None = None

def create_session(
        *,
        patch: PatchSession | None = None,
) -> Result:
    ''' Создаем сразу заполненный сценарий '''
    # проверяем patch на тип PatchSession
    if type(patch) is not PatchSession:
        return Err(meta='patch is not PatchSession', severity=Severity.ERROR)
    # проверяем owner_id на тип int
    if type(patch.owner_id) is not int:
        return Err(meta='owner_id is not int', severity=Severity.ERROR)
    # проверяем actor1_id на тип int
    if type(patch.actor1_id) is not int:
        return Err(meta='actor1_id is not int', severity=Severity.ERROR)
    # проверяем actor2_id на тип int
    if type(patch.actor2_id) is not int:
        return Err(meta='actor2_id is not int', severity=Severity.ERROR)
    # проверяем observer_ids на тип list
    if type(patch.observer_ids) is not list:
        return Err(meta='observer_ids is not list', severity=Severity.ERROR)
    # проверяем каждый observer_id на тип int
    for observer_id in patch.observer_ids:
        if type(observer_id) is not int:
            return Err(meta='observer_id is not int', severity=Severity.ERROR)
    # проверяем, что id наблюдателей не повторяются
    if len(set(patch.observer_ids)) != len(patch.observer_ids):
        return Err(meta='observer_ids are not unique', severity=Severity.ERROR)
    # актёр не может быть наблюдателем
    if patch.actor1_id in patch.observer_ids or patch.actor2_id in patch.observer_ids:
        return Err(meta='actor cannot be observer', severity=Severity.ERROR)

    # отправляем patch fields на валидацию и обрабатываем результат
    res = validate_fields(
        scenario_title=patch.title, scenario_version=patch.format_version, scenario_actor1=patch.actor1,
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

    owner_id = patch.owner_id
    actor1_id = patch.actor1_id
    actor2_id = patch.actor2_id
    observer_ids = patch.observer_ids
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
            owner_id, actor1_id,
            actor2_id, observer_ids,
            title, version,
            actor1, actor2,
            target1, target2,
            context1, context2,
            doc1, doc2
        )
    ):
        return Ok(meta="No fields to create session")

    # соединяем fields которые not None
    values = {}
    if owner_id is not None:
        values['owner_id'] = owner_id
    if actor1_id is not None:
        values['actor1_id'] = actor1_id
    if actor2_id is not None:
        values['actor2_id'] = actor2_id
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
            session = s.execute(
                insert(Session).values(**values).returning(Session)
            ).scalar_one_or_none()

            # наблюдатели хранятся отдельно от сессии
            if session is not None and observer_ids is not None:
                for observer_id in observer_ids:
                    s.execute(
                        insert(SessionObserver).values(session_id=session.id, user_id=observer_id)
                    )

        if session is None:
            return Err(meta='Session not found', severity=Severity.INFO)

        return Ok()

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


# Сейчас получить сессию может только владелец, но в будущем смогут и другие. Когда изменим способ хранения списка пользователей.
def get_session(
        *,
        user_id: int | None = None,
        session_id: int | None = None,
) -> Result[Session]:
    ''' Получить сессию по session_id '''
    # проверяем user_id на тип int
    if type(user_id) is not int:
        return Err(meta='user_id is not int', severity=Severity.ERROR)
    # проверяем session_id на тип int
    if type(session_id) is not int:
        return Err(meta='session_id is not int', severity=Severity.ERROR)

    # заключаем транзакцию в try
    try:
        with txn() as s:
            session = s.execute(
                select(Session).where(Session.id == session_id, Session.owner_id == user_id)
            ).scalar_one_or_none()

        if session is None:
            return Err(meta='Session not found', severity=Severity.ERROR)

        return Ok(value=session)

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)


# Сейчас получить сессию может только владелец, но в будущем смогут и другие. Когда изменим способ хранения списка пользователей.
def get_sessions(
        *,
        user_id: int | None = None,
) -> Result[list[Session] | str]:
    ''' Получить сессии по владельцу owner_id '''
    # проверяем user_id на тип int
    if type(user_id) is not int:
        return Err(meta='user_id is not int', severity=Severity.ERROR)

    # заключаем транзакцию в try
    try:
        with txn() as s:
            raw_sessions = s.execute(
                select(Session).where(Session.owner_id == user_id)
            ).scalars().all()

            sessions = []

            for session in raw_sessions:
                if session is not None:
                    s.expunge(session)
                    sessions.append(session)

        if not sessions:
            return Ok(meta='Sessions not found')

        return Ok(value=sessions)

    # критическая ошибка транзакции
    except SQLAlchemyError:
        return Err(meta=f"Database transaction failed", severity=Severity.CRITICAL)
    # критическая ошибка при транзакции
    except Exception:
        return Err(meta=f"Unexpected transaction error", severity=Severity.CRITICAL)