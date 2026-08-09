"""Документ сценария (.rpscene): скелет и валидация.

Формат v2:
{
  "format": "roleplay-scenario",
  "version": 2,
  "title": "...",
  "roles": {
    "actor1": { "label", "goal", "context", "body" },
    "actor2": { "label", "goal", "context", "body" }
  }
}

title / label / goal / context — обычные строки.
body — один TipTap/ProseMirror doc на роль.

Внутри body:
- обычные блоки: paragraph, heading, списки, hardBreak (inline), text
- section — вложенная секция (attrs.title), глубина ≤ 5; вместо старого callout
- image — картинка (attrs.src / alt / title), leaf

Даты создания/обновления в файл не входят (это дело БД).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.domain.scenario.constants import (
    FORMAT_NAME,
    FORMAT_VERSION,
    ROLE_ACTOR1,
    ROLE_ACTOR2,
    ROLE_KEYS,
)

_TEXT_LIMITS = {
    "title": 128,
    "label": 64,
    "goal": 1024,
    "context": 1024,
    "section_title": 128,
    "image_src": 2048,
    "image_alt": 512,
    "image_title": 512,
}
_BODY_TEXT_MAX = 20000
_BODY_CONTENT_MAX = 1000
_BODY_DEPTH_MAX = 20
_BODY_ERRORS_MAX = 25
_SECTION_DEPTH_MAX = 5

_BLOCKS = frozenset(
    {"paragraph", "heading", "bulletList", "orderedList", "section", "image"}
)
_INLINES = frozenset({"text", "hardBreak"})

# None = leaf: content быть не должно (или только пустой список).
# listItem = те же блоки, что doc/section (как paragraph block* в TipTap).
_ALLOWED_CHILDREN: dict[str, frozenset[str] | None] = {
    "doc": _BLOCKS,
    "section": _BLOCKS,
    "paragraph": _INLINES,
    "heading": _INLINES,
    "bulletList": frozenset({"listItem"}),
    "orderedList": frozenset({"listItem"}),
    "listItem": _BLOCKS,
    "text": None,
    "hardBreak": None,
    "image": None,
}

_BODY_NODES = frozenset(_ALLOWED_CHILDREN)
_BODY_MARKS = frozenset({"bold", "italic", "underline"})


def empty_body() -> dict[str, Any]:
    return {"type": "doc", "content": []}


def empty_section(*, title: str = "") -> dict[str, Any]:
    """Пустая вложенная секция (сворачиваемый контейнер в UI)."""
    return {
        "type": "section",
        "attrs": {"title": (title or "").strip()},
        "content": [],
    }


def empty_image(*, src: str = "", alt: str = "", title: str = "") -> dict[str, Any]:
    """Узел изображения (leaf)."""
    return {
        "type": "image",
        "attrs": {
            "src": (src or "").strip(),
            "alt": (alt or "").strip(),
            "title": (title or "").strip(),
        },
    }


def empty_actor(*, label: str = "") -> dict[str, Any]:
    return {
        "label": label,
        "goal": "",
        "context": "",
        "body": empty_body(),
    }


def empty_document(*, title: str = "") -> dict[str, Any]:
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "title": (title or "").strip(),
        "roles": {
            ROLE_ACTOR1: empty_actor(label="Роль 1"),
            ROLE_ACTOR2: empty_actor(label="Роль 2"),
        },
    }


def document_title(document: dict[str, Any]) -> str:
    title = document.get("title")
    return title.strip() if isinstance(title, str) else ""


def clone_document(document: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(document)


def coerce_document(document: Any) -> dict[str, Any]:
    """Привести произвольный JSON к скелету v2 (best-effort).

    Старый v1: meta.title, roles.observer, callout в body.
    Невалидный вход → пустой v2-документ.
    """
    if not isinstance(document, dict):
        return empty_document()

    src = deepcopy(document)
    title = src.get("title")
    if not isinstance(title, str) or not title.strip():
        meta = src.get("meta")
        if isinstance(meta, dict) and isinstance(meta.get("title"), str):
            title = meta["title"]
        else:
            title = ""

    roles_in = src.get("roles") if isinstance(src.get("roles"), dict) else {}
    roles_out: dict[str, Any] = {}
    for key, default_label in (
        (ROLE_ACTOR1, "Роль 1"),
        (ROLE_ACTOR2, "Роль 2"),
    ):
        raw = roles_in.get(key)
        roles_out[key] = _coerce_actor(raw, default_label=default_label)

    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "title": title.strip()[: _TEXT_LIMITS["title"]],
        "roles": roles_out,
    }


def _coerce_actor(role: Any, *, default_label: str) -> dict[str, Any]:
    base = empty_actor(label=default_label)
    if not isinstance(role, dict):
        return base

    for field in ("label", "goal", "context"):
        value = role.get(field)
        if isinstance(value, str):
            base[field] = value.strip()[: _TEXT_LIMITS[field]]

    body = role.get("body")
    if isinstance(body, dict) and body.get("type") == "doc":
        base["body"] = _coerce_body_node(body)
    return base


def _coerce_body_node(node: Any) -> Any:
    """Рекурсивно: callout → section, режем неизвестные узлы/marks."""
    if not isinstance(node, dict):
        return node

    node_type = node.get("type")
    if node_type == "callout":
        attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
        title = attrs.get("title") or attrs.get("label") or ""
        if not isinstance(title, str):
            title = ""
        out: dict[str, Any] = {
            "type": "section",
            "attrs": {"title": title.strip()[: _TEXT_LIMITS["section_title"]]},
        }
        content = node.get("content")
        if isinstance(content, list):
            out["content"] = [_coerce_body_node(child) for child in content]
        else:
            out["content"] = []
        return out

    if node_type not in _BODY_NODES:
        # Неизвестный блок — выкидываем, чтобы validate прошёл.
        return {"type": "paragraph"}

    out = {"type": node_type}
    if "attrs" in node and isinstance(node.get("attrs"), dict):
        out["attrs"] = deepcopy(node["attrs"])
    if node_type == "text":
        text = node.get("text")
        out["text"] = text if isinstance(text, str) else ""
        marks = node.get("marks")
        if isinstance(marks, list):
            cleaned = [
                deepcopy(mark)
                for mark in marks
                if isinstance(mark, dict) and mark.get("type") in _BODY_MARKS
            ]
            if cleaned:
                out["marks"] = cleaned
        return out

    content = node.get("content")
    if isinstance(content, list):
        out["content"] = [
            coerced
            for child in content
            if (coerced := _coerce_body_node(child)) is not None
        ]
    elif allowed := _ALLOWED_CHILDREN.get(node_type):
        if allowed is not None:
            out["content"] = []
    return out


def validate_document(document: Any) -> list[str]:
    """Пустой список = ок."""
    if not isinstance(document, dict):
        return ["document must be an object"]

    errors: list[str] = []

    if document.get("format") != FORMAT_NAME:
        errors.append(f"format must be {FORMAT_NAME!r}")

    version = document.get("version")
    if version != FORMAT_VERSION:
        errors.append(f"version must be {FORMAT_VERSION}")

    title = document.get("title")
    if not isinstance(title, str):
        errors.append("title must be a string")
    elif len(title) > _TEXT_LIMITS["title"]:
        errors.append("title is too long")

    roles = document.get("roles")
    if not isinstance(roles, dict):
        errors.append("roles must be an object")
        return errors

    for key in ROLE_KEYS:
        if key not in roles:
            errors.append(f"roles.{key} is required")
            continue
        errors.extend(_validate_actor(roles[key], f"roles.{key}"))

    return errors


def _validate_actor(role: Any, path: str) -> list[str]:
    if not isinstance(role, dict):
        return [f"{path} must be an object"]

    errors: list[str] = []
    for field in ("label", "goal", "context"):
        value = role.get(field)
        if not isinstance(value, str):
            errors.append(f"{path}.{field} must be a string")
        elif len(value) > _TEXT_LIMITS[field]:
            errors.append(f"{path}.{field} is too long")

    body = role.get("body")
    if not isinstance(body, dict):
        errors.append(f"{path}.body must be an object")
    elif body.get("type") != "doc":
        errors.append(f"{path}.body.type must be 'doc'")
    else:
        errors.extend(_validate_body(body, f"{path}.body", section_depth=0))
    return errors


def _validate_body(
    node: Any,
    path: str,
    *,
    depth: int = 0,
    section_depth: int = 0,
) -> list[str]:
    if not isinstance(node, dict) or depth > _BODY_DEPTH_MAX:
        return [f"{path} has invalid structure"]

    errors: list[str] = []
    node_type = node.get("type")
    if node_type not in _BODY_NODES:
        errors.append(f"{path}.type is not allowed")
        return errors

    child_section_depth = section_depth
    if node_type == "section":
        if section_depth >= _SECTION_DEPTH_MAX:
            errors.append(f"{path} exceeds max section depth ({_SECTION_DEPTH_MAX})")
        errors.extend(_validate_section_attrs(node.get("attrs"), path))
        child_section_depth = section_depth + 1
    elif node_type == "image":
        errors.extend(_validate_image_attrs(node.get("attrs"), path))
    elif node_type == "heading":
        errors.extend(_validate_heading_attrs(node.get("attrs"), path))
    elif node_type == "text":
        errors.extend(_validate_text_node(node, path))

    if "marks" in node and node_type != "text":
        errors.append(f"{path}.marks is only allowed on text")

    allowed = _ALLOWED_CHILDREN[node_type]
    content = node.get("content", None)

    if allowed is None:
        if content not in (None, []):
            errors.append(f"{path} must not have content")
        return errors

    if content is None:
        content = []
    if not isinstance(content, list) or len(content) > _BODY_CONTENT_MAX:
        errors.append(f"{path}.content is invalid")
        return errors

    if node_type == "listItem" and not content:
        errors.append(f"{path} listItem must not be empty")

    for index, child in enumerate(content):
        child_path = f"{path}.content[{index}]"
        if not isinstance(child, dict):
            errors.append(f"{child_path} has invalid structure")
            if len(errors) >= _BODY_ERRORS_MAX:
                break
            continue
        child_type = child.get("type")
        if child_type not in allowed:
            errors.append(
                f"{child_path}.type {child_type!r} is not allowed inside {node_type}"
            )
        else:
            errors.extend(
                _validate_body(
                    child,
                    child_path,
                    depth=depth + 1,
                    section_depth=child_section_depth,
                )
            )
        if len(errors) >= _BODY_ERRORS_MAX:
            break
    return errors


def _validate_text_node(node: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    text = node.get("text")
    if not isinstance(text, str):
        errors.append(f"{path}.text must be a string")
    elif len(text) > _BODY_TEXT_MAX:
        errors.append(f"{path}.text is too long")

    if "marks" in node:
        marks = node.get("marks")
        if not isinstance(marks, list) or any(
            not isinstance(mark, dict) or mark.get("type") not in _BODY_MARKS
            for mark in marks
        ):
            errors.append(f"{path}.marks is invalid")
    return errors


def _validate_heading_attrs(attrs: Any, path: str) -> list[str]:
    if not isinstance(attrs, dict):
        return [f"{path}.attrs must be an object"]
    level = attrs.get("level")
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 6:
        return [f"{path}.attrs.level must be an integer 1..6"]
    return []


def _validate_section_attrs(attrs: Any, path: str) -> list[str]:
    if not isinstance(attrs, dict):
        return [f"{path}.attrs must be an object"]
    title = attrs.get("title")
    if not isinstance(title, str):
        return [f"{path}.attrs.title must be a string"]
    if len(title) > _TEXT_LIMITS["section_title"]:
        return [f"{path}.attrs.title is too long"]
    return []


def _validate_image_attrs(attrs: Any, path: str) -> list[str]:
    if not isinstance(attrs, dict):
        return [f"{path}.attrs must be an object"]

    errors: list[str] = []
    src = attrs.get("src")
    if not isinstance(src, str) or not src.strip():
        errors.append(f"{path}.attrs.src must be a non-empty string")
    elif len(src) > _TEXT_LIMITS["image_src"]:
        errors.append(f"{path}.attrs.src is too long")

    for key, limit_key in (("alt", "image_alt"), ("title", "image_title")):
        if key not in attrs or attrs.get(key) is None:
            continue
        value = attrs.get(key)
        if not isinstance(value, str):
            errors.append(f"{path}.attrs.{key} must be a string")
        elif len(value) > _TEXT_LIMITS[limit_key]:
            errors.append(f"{path}.attrs.{key} is too long")
    return errors
