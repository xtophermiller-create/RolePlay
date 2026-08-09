"""Безопасный commit: гонка unique → rollback, без 500."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.extensions import db


def try_commit() -> bool:
    """commit(); при IntegrityError — rollback и False."""
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False
