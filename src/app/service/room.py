
from __future__ import annotations

from copy import deepcopy
from sqlalchemy.exc import SQLAlchemyError
import random
import string
from ..domain import (
    SCENARIO_DEFAULT,
    SCENARIO_TYPES,
    Scenario,
    Session,
    RoomManager,
    Room
)
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

        code = _generate_code()
        room = Room(
            code=code,
            owner_id=user_id,
            player_ids={user_id},
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

        if user_id != manager._rooms[code].owner_id:
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

        room.player_ids.add(user_id)
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
            room.player_ids.discard(user_id)
            room.observer_ids.discard(user_id)
            room.actor1_id.discard(user_id)
            room.actor2_id.discard(user_id)
            return Ok()