from __future__ import annotations

from flask import session
from flask_socketio import ConnectionRefusedError, Namespace, emit, join_room
from ..app import socketio
from ..service.draft import open_draft, save_draft, update_draft
from ..service.helper import Err
from ..service.scenario import PatchScenario
from .helpers import err_message

NAMESPACE = '/editor'

# поля черновика, которые клиент может менять; имена совпадают с PatchScenario
PATCH_FIELDS = ('title', 'actor1', 'actor2', 'target1', 'target2', 'context1', 'context2', 'doc1', 'doc2')


def draft_state(draft) -> dict:
    ''' Явный dict для клиента: только поля сценария и revision '''
    state = {name: getattr(draft, name) for name in PATCH_FIELDS}
    state['revision'] = draft.revision
    return state


def _room(scenario_id: int) -> str:
    return str(scenario_id)


def _error(res: Err) -> dict:
    return {'ok': False, 'error': err_message(res)}


class EditorNamespace(Namespace):
    ''' Редактирование черновика сценария владельцем; в базу пишет service '''

    def on_connect(self, auth=None):
        # CSRF на сокет не действует: пускаем только владельца, service проверяет по user_id из сессии
        user_id = session.get('user_id')
        scenario_id = auth.get('scenario_id') if isinstance(auth, dict) else None
        res = open_draft(user_id=user_id, scenario_id=scenario_id)
        if not res:
            raise ConnectionRefusedError('scenario not available')

        join_room(_room(scenario_id))
        emit('state', draft_state(res.value))

    def on_update(self, data=None):
        ''' data: {scenario_id, revision, patch: {поле: значение}}; отсутствующее поле — «не менять» '''
        data = data if isinstance(data, dict) else {}
        patch = data.get('patch') if isinstance(data.get('patch'), dict) else {}
        scenario_id = data.get('scenario_id')
        user_id = session.get('user_id')

        res = update_draft(
            user_id=user_id,
            scenario_id=scenario_id,
            patch=PatchScenario(**{name: patch.get(name) for name in PATCH_FIELDS}),
            revision=data.get('revision'),
        )
        if not res:
            # клиент получает актуальный черновик, чтобы продолжить с верной revision
            draft = open_draft(user_id=user_id, scenario_id=scenario_id)
            if draft:
                emit('state', draft_state(draft.value))
            return _error(res)

        # другие вкладки этого сценария получают новое состояние
        draft = open_draft(user_id=user_id, scenario_id=scenario_id)
        if draft:
            emit('state', draft_state(draft.value), to=_room(scenario_id), include_self=False)
        return {'ok': True, 'revision': res.value}

    def on_save(self, data=None):
        data = data if isinstance(data, dict) else {}
        res = save_draft(user_id=session.get('user_id'), scenario_id=data.get('scenario_id'))
        if not res:
            return _error(res)
        return {'ok': True}


def register_editor_socket() -> None:
    socketio.on_namespace(EditorNamespace(NAMESPACE))
