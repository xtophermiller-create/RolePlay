from __future__ import annotations

from flask import session
from flask_socketio import ConnectionRefusedError, Namespace, emit, join_room
from ..app import socketio
from ..domain import Room
from ..service.room import get_room

NAMESPACE = '/room'


def _role_key(user_id: int, *, actor1_ids: set[int], actor2_ids: set[int], observer_ids: set[int]) -> str | None:
    if user_id in actor1_ids:
        return 'actor1'
    if user_id in actor2_ids:
        return 'actor2'
    if user_id in observer_ids:
        return 'observer'
    return None


def room_state(room: Room) -> dict:
    ''' Явный dict для клиента: без id пользователей и без Room целиком '''
    # копии: другой поток может изменить комнату во время сборки
    players = list(room.players.items())
    roles = {
        'actor1_ids': set(room.actor1_id),
        'actor2_ids': set(room.actor2_id),
        'observer_ids': set(room.observer_ids),
    }
    return {
        'title': room.title,
        'scenario_id': room.scenario_id,
        'is_started': room.is_started,
        'actor1': room.actor1,
        'actor2': room.actor2,
        'target1': room.target1,
        'target2': room.target2,
        'context1': room.context1,
        'context2': room.context2,
        'doc1': room.doc1,
        'doc2': room.doc2,
        'players': [
            {
                'nickname': player['nickname'],
                'role': _role_key(user_id, **roles),
                'is_owner': user_id == room.owner_id,
                'left': player['left'],
            }
            for user_id, player in players
        ],
    }


def not_in_room(room: Room, user_id: int) -> bool:
    ''' Ушедший из активной сессии для страницы и сокета — как посторонний '''
    player = room.players.get(user_id)
    if player is None:
        return True
    return bool(room.is_started and player.get('left'))


def broadcast_room(code: str) -> None:
    ''' Разослать участникам текущее состояние; если комнаты уже нет — сообщить о закрытии '''
    res = get_room(code=code)
    if res:
        socketio.emit('state', room_state(res.value), to=code, namespace=NAMESPACE)
    else:
        socketio.emit('closed', to=code, namespace=NAMESPACE)


class RoomNamespace(Namespace):
    ''' Только чтение: все изменения идут обычными POST формами '''

    def on_connect(self, auth=None):
        # CSRF на сокет не действует: пускаем только участника комнаты из сессии
        user_id = session.get('user_id')
        code = auth.get('code') if isinstance(auth, dict) else None
        res = get_room(code=code)
        if user_id is None or not res or not_in_room(res.value, user_id):
            raise ConnectionRefusedError('not a room member')

        join_room(code)
        emit('state', room_state(res.value))


def register_room_socket() -> None:
    socketio.on_namespace(RoomNamespace(NAMESPACE))
