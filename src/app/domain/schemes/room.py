from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from ..models import SCENARIO_DEFAULT, SCENARIO_TYPES
import random
import string

CODE_CHARS = string.ascii_letters + string.digits


@dataclass
class Room:
    ''' Текущее состояние одной активной комнаты '''
    code: str
    owner_id: int
    scenario_id: int | None = None

    player_ids: set[int] = field(default_factory=set)
    observer_ids: set[int] = field(default_factory=set)
    actor1_id: set[int] = field(default_factory=set)
    actor2_id: set[int] = field(default_factory=set)

    is_started: bool = False

    title: str  = SCENARIO_DEFAULT['TITLE']
    actor1: str = SCENARIO_DEFAULT['ACTOR1']
    actor2: str = SCENARIO_DEFAULT['ACTOR2']
    target1: str | None = None
    target2: str | None = None
    context1: str | None = None
    context2: str | None = None
    doc1: dict = SCENARIO_TYPES['DOC']
    doc2: dict = SCENARIO_TYPES['DOC']


class RoomManager:
    ''' Хранит активные комнаты в оперативной памяти '''
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self.lock = RLock()

    # def _generate_code(self) -> str:
    #     ''' Генерирует уникальный код  '''
    #     while True:
    #         code = ''.join(random.choices(CODE_CHARS, k=8))
    #         if code not in self._rooms:
    #             return code
    #
    # def create(self, owner_id: int) -> Room:
    #     ''' Создать комнату с уникальным кодом '''
    #     with self.lock:
    #         code = self._generate_code()
    #         room = Room(
    #             code=code,
    #             owner_id=owner_id,
    #         )
    #
    #         self._rooms[code] = room
    #         return room
    #
    # def get(self, code: str) -> Room | None:
    #     ''' Получить комнату по коду '''
    #     with self.lock:
    #         return self._rooms.get(code)
    #
    # def remove(self, code: str) -> bool:
    #     ''' Удалить комнату из оперативной памяти '''
    #     with self.lock:
    #         return self._rooms.pop(code, None) is not None
    @property
    def rooms(self):
        return self._rooms