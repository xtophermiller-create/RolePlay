from __future__ import annotations

import secrets
from copy import deepcopy
import random
import string
from .profile import get_profile
from .session import create_session, PatchSession
from .scenario import get_scenario
from ..domain import RoomManager, Room, Scenario, SCENARIO_DEFAULT, SCENARIO_TYPES
from .helper import Err, Ok, Result, Severity
from time import monotonic, sleep
from threading import Thread

manager = RoomManager()
ROOM_IDLE_TIMEOUT = 120 * 60  # 2 часа


def cleanup_idle_rooms():
    ''' Удаляем комнаты, бездействующие дольше установленного времени '''
    now = monotonic()

    with manager.lock:
        for code, room in list(manager._rooms.items()):
            if now - room.last_activity >= ROOM_IDLE_TIMEOUT:
                manager._rooms.pop(code)


def room_cleanup_worker():
    while True:
        sleep(60)
        cleanup_idle_rooms()


def start_room_cleanup():
    Thread(
        target=room_cleanup_worker,
        daemon=True
    ).start()


def create_room(
        *,
        user_id: int | None = None,
) -> Result[Room]:
    ''' Создаёт комнату с уникальным кодом '''
    if type(user_id) is not int:
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)

    res = get_profile(user_id=user_id)
    if not res:
        return Err(meta='profile not found', severity=Severity.ERROR)
    nickname, avatar = res.value

    with manager.lock:
        def _generate_code() -> str:
            ''' Генерирует уникальный код  '''
            while True:
                code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
                if code not in manager._rooms:
                    return code

        for code, room in list(manager._rooms.items()):
            if room.owner_id == user_id:
                manager._rooms.pop(code)

        player = {
            user_id: {
                'nickname': nickname,
                'avatar': avatar,
                'left': False,
            }
        }

        code = _generate_code()
        room = Room(
            code=code,
            owner_id=user_id,
            players=player,
            observer_ids={user_id},
            last_activity=monotonic()
        )

        manager._rooms[code] = room

        return Ok(value=room)


def delete_room(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result:
    if type(user_id) is not int:
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if type(code) is not str:
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
    if type(code) is not str:
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
    if type(user_id) is not int:
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if type(code) is not str:
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    res = get_profile(user_id=user_id)
    if not res:
        return Err(meta='profile not found', severity=Severity.ERROR)
    nickname, avatar = res.value

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if room.is_started:
            return Err(meta='roleplay already started', severity=Severity.INFO)

        room.players.pop(user_id, None)
        room.observer_ids.discard(user_id)
        room.actor1_id.discard(user_id)
        room.actor2_id.discard(user_id)

        player = {
            'nickname': nickname,
            'avatar': avatar,
            'left': False
        }

        room.players[user_id] = player
        room.observer_ids.add(user_id)

        room.last_activity = monotonic()

        return Ok(value=room)


def leave(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result:
    if type(user_id) is not int:
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if type(code) is not str:
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)

        room.last_activity = monotonic()

        if user_id == room.owner_id:
            delete_room(user_id=user_id, code=code)
            return Ok()

        if room.is_started and room.players.get(user_id, None):
            room.players[user_id]['left'] = True
            return Ok()

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
    if type(user_id) is not int:
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if type(role) is not int:
        return Err(meta='role is missing or invalid', severity=Severity.ERROR)
    if type(code) is not str:
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)
    if role not in roles:
        return Err(meta='role not found', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if room.is_started:
            return Err(meta='roleplay already started', severity=Severity.INFO)

        if not room.players.get(user_id):
            return Err(meta='player not found', severity=Severity.INFO)

        room.observer_ids.discard(user_id)
        room.actor1_id.discard(user_id)
        room.actor2_id.discard(user_id)

        room.last_activity = monotonic()

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

isinstance()
def choose_scenario(
        *,
        user_id: int | None = None,
        code: str | None = None,
        scenario_id: int | None = None,
) -> Result:
    if type(user_id) is not int:
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if type(code) is not str:
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)
    if type(scenario_id) is not int:
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
        room.scenario_id = scenario.id
        room.title = scenario.title
        room.actor1 = scenario.actor1
        room.actor2 = scenario.actor2
        room.target1 = scenario.target1
        room.target2 = scenario.target2
        room.context1 = scenario.context1
        room.context2 = scenario.context2
        room.doc1 = deepcopy(scenario.document1)
        room.doc2 = deepcopy(scenario.document2)

        room.last_activity = monotonic()

        return Ok()


def start_session(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result:
    if type(user_id) is not int:
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if type(code) is not str:
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if user_id != room.owner_id:
            return Err(meta='room not found', severity=Severity.ERROR)
        if room.is_started:
            return Err(meta='roleplay already started', severity=Severity.INFO)
        if len(room.actor1_id) != 1:
            return Err(meta='Can be only one actor', severity=Severity.ERROR)
        if len(room.actor2_id) != 1:
            return Err(meta='Can be only one actor', severity=Severity.ERROR)
        # Проверяем уникален ли пользователь во всех группах
        if (
                room.actor1_id & room.actor2_id
                or room.actor1_id & room.observer_ids
                or room.actor2_id & room.observer_ids
        ):
            return Err(meta='Participant has multiple roles', severity=Severity.ERROR)
        assigned_ids = room.actor1_id | room.actor2_id | room.observer_ids
        if assigned_ids != set(room.players):
            return Err(meta='Participants are not fully assigned to roles', severity=Severity.ERROR)

        room.is_started = True

        room.last_activity = monotonic()

        return Ok()


def finish_session(
        *,
        user_id: int | None = None,
        code: str | None = None,
) -> Result:
    if type(user_id) is not int:
        return Err(meta='user_id is missing or invalid', severity=Severity.ERROR)
    if type(code) is not str:
        return Err(meta='code is missing or invalid', severity=Severity.ERROR)

    with manager.lock:
        room = manager._rooms.get(code)
        if room is None:
            return Err(meta='room not found', severity=Severity.INFO)
        if user_id != room.owner_id:
            return Err(meta='room not found', severity=Severity.ERROR)
        if not room.is_started:
            return Err(meta='Roleplay not active', severity=Severity.INFO)

        patch = PatchSession(
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
            doc1=deepcopy(room.doc1),
            doc2=deepcopy(room.doc2)
        )

        room.scenario_id = None
        room.title = SCENARIO_DEFAULT['TITLE']
        room.actor1 = SCENARIO_DEFAULT['ACTOR1']
        room.actor2 = SCENARIO_DEFAULT['ACTOR2']
        room.target1 = None
        room.target2 = None
        room.context1 = None
        room.context2 = None
        room.doc1 = deepcopy(SCENARIO_TYPES['DOC'])
        room.doc2 = deepcopy(SCENARIO_TYPES['DOC'])

        for key, value in list(room.players.items()):
            if value['left']:
                room.players.pop(key, None)
                room.observer_ids.discard(key)
                room.actor1_id.discard(key)
                room.actor2_id.discard(key)

        room.last_activity = monotonic()

        room.is_started = False

    res = create_session(patch=patch)
    if not res:
        return Err(meta=res.meta, severity=Severity.ERROR)

    return Ok()