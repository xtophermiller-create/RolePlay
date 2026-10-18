''' Обертка для результата функции '''

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar('T')

class Severity(StrEnum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'

class Action(StrEnum):
    NONE = 'none'


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T | None = None
    meta: str | None = None
    ok: bool = True 

    def __bool__(self) -> bool:
        return True

@dataclass(frozen=True, slots=True)
class Err(Generic[T]):
    value: T | None = None
    meta: str | None = None
    severity: Severity | None = Severity.ERROR
    actions: tuple[Action] | None = None
    ok: bool = False

    def __bool__(self) -> bool:
        return False


Result = Ok[T] | Err[T]