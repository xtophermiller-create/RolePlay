"""Результат операции сервиса: Ok(value) / Err(code). bool(result) == ok."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T
    ok: bool = True
    error: str | None = None

    def __bool__(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class Err:
    error: str
    ok: bool = False
    value: None = None

    def __bool__(self) -> bool:
        return False


Result = Ok[T] | Err
