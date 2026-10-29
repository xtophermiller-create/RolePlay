from __future__ import annotations

from copy import deepcopy
import random
import string
from .profile import get_profile
from .session import create_session
from .scenario import get_scenario
from ..domain import RoomManager, Room, Scenario, SCENARIO_DEFAULT, SCENARIO_TYPES
from .helper import Err, Ok, Result, Severity

manager = RoomManager()


def create_room(
        *,
        user_id: int | None = None,
) -> Result[Room]:
    ''' Создаёт комнату с уникальным кодом '''
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        def _generate_code() -> str:
            ''' Генерирует уникальный код  '''
            while True:
                code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                if code not in manager._rooms:
                    return code

        for code, room in list(manager._rooms.items()):
            if room.owner_id == user_id:
                manager._rooms.pop(code)

        res = get_profile(user_id=user_id)
        if not res:
            return Err(meta='profile not found', severity=Severity.ERROR)
        nickname, avatar = res.value

        player = {
            user_id: {
                'nickname': nickname,
                'avatar': avatar
            }
        }

        code = _generate_code()
        room = Room(
            code=code,
            owner_id=user_id,
            players=player,
            observer_ids={user_id},
        )

        manager._rooms[code] = room

        return Ok(value=room)


def delete_room(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result:
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if not code or not isinstance(code, str):
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)

        if user_id != room.owner_id:
            return Err(meta='room not found', severity=Severity.ERROR)

        manager._rooms.pop(code, None)

        return Ok()


def get_room(
        *,
        code: str | None = None,
) -> Result[Room]:
    if not code or not isinstance(code, str):
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)

        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)

        return Ok(value=room)


def connect(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result[Room]:
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if not code or not isinstance(code, str):
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if room.is_started:
            return Err(meta='roleplay already started', severity=Severity.INFO)

        res = get_profile(user_id=user_id)
        if not res:
            return Err(meta='profile not found', severity=Severity.ERROR)
        nickname, avatar = res.value

        player = {
            'nickname': nickname,
            'avatar': avatar
        }

        room.players[user_id] = player
        room.observer_ids.add(user_id)

        return Ok(value=room)


def leave(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result:
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if not code or not isinstance(code, str):
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)

        if user_id == room.owner_id:
            delete_room(user_id=user_id, code=code)
            return Ok()
        else:
            room.players.pop(user_id, None)
            room.observer_ids.discard(user_id)
            room.actor1_id.discard(user_id)
            room.actor2_id.discard(user_id)
            return Ok()


def choose_role(
        *,
        user_id: int | None = None,
        code: str | None = None,
        role: int | None = None,
) -> Result:
    roles = [1, 2, 3]
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if not role or not isinstance(role, int):
        return Err(meta='role is missing or invalid', severity=Severity.ERROR)
    if not code or not isinstance(code, str):
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)
    if role not in roles:
        return Err(meta='role not found', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if room.is_started:
            return Err(meta='roleplay already started', severity=Severity.INFO)

        room.observer_ids.discard(user_id)
        room.actor1_id.discard(user_id)
        room.actor2_id.discard(user_id)

        if role == 1:
            room.actor1_id.add(user_id)
            return Ok()
        if role == 2:
            room.actor2_id.add(user_id)
            return Ok()
        if role == 3:
            room.observer_ids.add(user_id)
            return Ok()

        room.observer_ids.add(user_id)
        return Err(meta='role not found', severity=Severity.ERROR)


def choose_scenario(
        *,
        user_id: int | None = None,
        code: str | None = None,
        scenario_id: int | None = None,
) -> Result:
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if not code or not isinstance(code, str):
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)
    if not scenario_id or not isinstance(scenario_id, int):
        return Err(meta='scenario_id is missing or invalid', severity=Severity.ERROR)

    scenario = get_scenario(user_id=user_id, scenario_id=scenario_id)
    if not scenario:
        return Err(meta=scenario.meta, severity=Severity.ERROR)
    scenario: Scenario = scenario.value

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if user_id != room.owner_id:
            return Err(meta='room not found', severity=Severity.ERROR)
        if room.is_started:
            return Err(meta='roleplay already started', severity=Severity.INFO)

        room.format_version = scenario.format_version
        room.scenario_id = scenario.scenario_id
        room.title = scenario.title
        room.actor1 = scenario.actor1
        room.actor2 = scenario.actor2
        room.target1 = scenario.target1
        room.target2 = scenario.target2
        room.context1 = scenario.context1
        room.context2 = scenario.context2
        room.doc1 = deepcopy(scenario.doc1)
        room.doc2 = deepcopy(scenario.doc2)

        return Ok()


def start_session(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result:
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if not code or not isinstance(code, str):
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if user_id != room.owner_id:
            return Err(meta='room not found', severity=Severity.ERROR)
        if room.is_started:
            return Err(meta='roleplay already started', severity=Severity.INFO)

        room.is_started = True
        return Ok()


def finish_session(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result:
    if not user_id or not isinstance(user_id, int):
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if not code or not isinstance(code, str):
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if user_id != room.owner_id:
            return Err(meta='room not found', severity=Severity.ERROR)
        if not room.is_started:
            return Err(meta='roleplay not active', severity=Severity.INFO)

        res = create_session(
            owner_id=room.owner_id,
            actor1_id=next(iter(room.actor1_id)),
            actor2_id=next(iter(room.actor2_id)),
            observer_ids=list(room.observer_ids),
            title=room.title,
            format_version=room.format_version,
            actor1=room.actor1,
            actor2=room.actor2,
            target1=room.target1,
            target2=room.target2,
            context1=room.context1,
            context2=room.context2,
            doc1=room.doc1,
            doc2=room.doc2,
        )

        room.scenario_id = None
        room.title = SCENARIO_DEFAULT['TITLE']
        room.actor1 = SCENARIO_DEFAULT['ACTOR1']
        room.actor2 = SCENARIO_DEFAULT['ACTOR2']
        room.target1 = None
        room.target2 = None
        room.context1 = None
        room.context2 = None
        room.doc1 = SCENARIO_TYPES['DOC']
        room.doc2 = SCENARIO_TYPES['DOC']

        if not res:
            room.is_started = False
            return Err(meta=res.meta, severity=Severity.ERROR)
        room.is_started = False
        return Ok()