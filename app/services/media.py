"""
Медиафайлы → storage/media/:
  avatars/   — аватарки (u{user_id}_{uuid}.jpg)
  scenarios/ — картинки в теле сценария (s{scenario_id}_{uuid}.jpg)
"""

from __future__ import annotations

import os
import re
import uuid
import warnings
from typing import Any

from flask import current_app
from PIL import Image

from app.domain.models import User
from app.extensions import db

AVATAR_SIZE = 512
AVATAR_REL_DIR = "avatars"
SCENARIO_IMAGE_REL_DIR = "scenarios"
SCENARIO_IMAGE_MAX_EDGE = 1600
SCENARIO_IMAGE_NAME_RE = re.compile(r"^s(\d+)_([a-f0-9]{32})\.jpg$")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def _project_media_dir() -> str:
    return current_app.config["MEDIA_DIR"]


def _avatars_abs_dir() -> str:
    path = os.path.join(_project_media_dir(), AVATAR_REL_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _abs_from_rel(rel_path: str) -> str:
    rel = (rel_path or "").replace("\\", "/").lstrip("/")
    return os.path.join(_project_media_dir(), *rel.split("/"))


def _new_user_rel_path(user: User) -> str:
    return f"{AVATAR_REL_DIR}/u{user.user_id}_{uuid.uuid4().hex}.jpg"


def _remove_file(rel_path: str | None) -> None:
    if not rel_path:
        return
    abs_path = _abs_from_rel(rel_path)
    if os.path.isfile(abs_path):
        try:
            os.remove(abs_path)
        except OSError:
            pass


def _load_upload(upload: Any) -> Image.Image | None:
    if upload is None:
        return None
    filename = (getattr(upload, "filename", None) or "").strip()
    if not filename:
        return None
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    try:
        stream = upload.stream
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)
        if size > current_app.config["MAX_AVATAR_BYTES"]:
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(stream)
            width, height = image.size
            if (
                width <= 0
                or height <= 0
                or width > current_app.config["MAX_AVATAR_DIMENSION"]
                or height > current_app.config["MAX_AVATAR_DIMENSION"]
                or width * height > current_app.config["MAX_AVATAR_PIXELS"]
            ):
                return None
            image.load()
            return image
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return None


def _to_square_512(image: Image.Image) -> Image.Image:
    image = image.copy().convert("RGB")
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    square = image.crop((left, top, left + side, top + side))
    return square.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)


def _save_user_avatar_file(user: User, image: Image.Image) -> str:
    _avatars_abs_dir()
    new_rel = _new_user_rel_path(user)
    new_abs = _abs_from_rel(new_rel)
    old_rel = user.avatar
    image.save(new_abs, format="JPEG", quality=90, optimize=True)
    if old_rel and old_rel.replace("\\", "/") != new_rel:
        _remove_file(old_rel)
    return new_rel


def set_user_avatar(user_id: int, upload: Any) -> bool:
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return False
    raw = _load_upload(upload)
    if raw is None:
        return False
    user.avatar = _save_user_avatar_file(user, _to_square_512(raw))
    db.session.commit()
    return True


def delete_user_avatar(user_id: int) -> bool:
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return False
    _remove_file(user.avatar)
    user.avatar = None
    db.session.commit()
    return True


def user_avatar_abs_path(user: User) -> str | None:
    if not user or not user.avatar:
        return None
    abs_path = _abs_from_rel(user.avatar)
    if not os.path.isfile(abs_path):
        return None
    return abs_path


def _scenarios_abs_dir() -> str:
    path = os.path.join(_project_media_dir(), SCENARIO_IMAGE_REL_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _fit_max_edge(image: Image.Image, max_edge: int) -> Image.Image:
    """RGB, длинная сторона ≤ max_edge (без кропа)."""
    image = image.copy()
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        alpha = image.split()[-1]
        background.paste(image.convert("RGBA"), mask=alpha)
        image = background
    elif image.mode == "P":
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    else:
        image = image.convert("RGB")

    width, height = image.size
    longest = max(width, height)
    if longest > max_edge:
        scale = max_edge / longest
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.LANCZOS,
        )
    return image


def save_scenario_image(scenario_id: int, upload: Any) -> str | None:
    """Сохранить картинку сценария. Возвращает имя файла (basename) или None."""
    raw = _load_upload(upload)
    if raw is None:
        return None

    image = _fit_max_edge(raw, SCENARIO_IMAGE_MAX_EDGE)
    _scenarios_abs_dir()
    filename = f"s{int(scenario_id)}_{uuid.uuid4().hex}.jpg"
    rel = f"{SCENARIO_IMAGE_REL_DIR}/{filename}"
    abs_path = _abs_from_rel(rel)
    try:
        image.save(abs_path, format="JPEG", quality=85, optimize=True)
    except OSError:
        return None
    return filename


def scenario_image_abs_path(filename: str) -> str | None:
    name = os.path.basename((filename or "").strip())
    if not SCENARIO_IMAGE_NAME_RE.match(name):
        return None
    abs_path = _abs_from_rel(f"{SCENARIO_IMAGE_REL_DIR}/{name}")
    if not os.path.isfile(abs_path):
        return None
    return abs_path
