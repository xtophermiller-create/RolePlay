"""Чистые операции над ролями в документе сценария (без I/O)."""

from __future__ import annotations
from typing import Any
from app.domain.scenario.constants import ROLE_ACTOR1, ROLE_ACTOR2, ROLE_KEYS
from app.domain.scenario.document import empty_body

ACTOR_KEYS = ROLE_KEYS


def get_roles(document: dict[str, Any]) -> dict[str, Any]:
    roles = document.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("roles_missing")
    return roles


def get_role(document: dict[str, Any], role_key: str) -> dict[str, Any]:
    if role_key not in ROLE_KEYS:
        raise ValueError("unknown_role")
    role = get_roles(document).get(role_key)
    if not isinstance(role, dict):
        raise ValueError("role_missing")
    return role


def is_actor(role_key: str) -> bool:
    return role_key in ACTOR_KEYS


def set_scenario_title(document: dict[str, Any], title: str) -> None:
    document["title"] = (title or "").strip()


def set_actor_fields(
    document: dict[str, Any],
    role_key: str,
    *,
    label: str | None = None,
    goal: str | None = None,
    context: str | None = None,
    body: dict[str, Any] | None = None,
) -> None:
    """Обновить поля роли. None = не трогать поле."""
    if not is_actor(role_key):
        raise ValueError("not_an_actor")
    role = get_role(document, role_key)

    if label is not None:
        role["label"] = label.strip()
    if goal is not None:
        role["goal"] = goal.strip()
    if context is not None:
        role["context"] = context.strip()
    if body is not None:
        if not isinstance(body, dict) or body.get("type") != "doc":
            raise ValueError("invalid_body")
        role["body"] = body


def plain_text_to_body(text: str) -> dict[str, Any]:
    """Простой текст → TipTap doc (абзацы по пустой строке)."""
    raw = text if isinstance(text, str) else ""
    chunks = raw.split("\n\n") if raw else [""]
    content: list[dict[str, Any]] = []
    for chunk in chunks:
        piece = "\n".join(chunk.split("\n"))
        if piece:
            content.append(
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": piece}],
                }
            )
        else:
            content.append({"type": "paragraph"})
    if not content:
        return empty_body()
    return {"type": "doc", "content": content}


def set_actor_body_text(document: dict[str, Any], role_key: str, text: str) -> None:
    set_actor_fields(document, role_key, body=plain_text_to_body(text))


# Явные реэкспорты ключей ролей для удобства импорта из roles.
__all__ = [
    "ACTOR_KEYS",
    "ROLE_ACTOR1",
    "ROLE_ACTOR2",
    "ROLE_KEYS",
    "get_roles",
    "get_role",
    "is_actor",
    "set_scenario_title",
    "set_actor_fields",
    "plain_text_to_body",
    "set_actor_body_text",
]
