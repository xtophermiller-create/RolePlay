from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from ..models import SCENARIO_DEFAULT, SCENARIO_TYPES
from time import monotonic
import string

CODE_CHARS = string.ascii_letters + string.digits


@dataclass
class Room:
    ''' Текущее состояние одной активной комнаты '''
    code: str
    owner_id: int
    scenario_id: int | None = None

    players: dict[int, dict[str, Any]] = field(default_factory=dict)

    observer_ids: set[int] = field(default_factory=set)
    actor1_id: set[int] = field(default_factory=set)
    actor2_id: set[int] = field(default_factory=set)

    is_started: bool = False

    format_version: int = SCENARIO_DEFAULT['VERSION']
    title: str  = SCENARIO_DEFAULT['TITLE']
    actor1: str = SCENARIO_DEFAULT['ACTOR1']
    actor2: str = SCENARIO_DEFAULT['ACTOR2']
    target1: str | None = None
    target2: str | None = None
    context1: str | None = None
    context2: str | None = None
    doc1: dict = field(default_factory=lambda: deepcopy(SCENARIO_TYPES['DOC']))
    doc2: dict = field(default_factory=lambda: deepcopy(SCENARIO_TYPES['DOC']))

    last_activity: float = field(default_factory=monotonic)


class RoomManager:
    ''' Хранит активные комнаты в оперативной памяти '''
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self.lock = RLock()