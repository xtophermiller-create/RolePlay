from __future__ import annotations

from ..models import SCENARIO_DEFAULT, SCENARIO_TYPES

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from time import monotonic


@dataclass
class Draft:
    ''' Текущее состояние черновика в редакторе '''
    scenario_id: int
    owner_id: int

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

    revision: int = 0

    last_activity: float = field(default_factory=monotonic)


class DraftManager:
    ''' Хранит активные черновики редактора в оперативной памяти '''
    def __init__(self) -> None:
        self._drafts: dict[str, Draft] = {}
        self.lock = RLock()