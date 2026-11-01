from __future__ import annotations

from contextlib import contextmanager
from sqlalchemy.orm import Session
from ...app import db


@contextmanager
def transaction():
    with Session(db.engine, expire_on_commit=False) as session:
        with session.begin():
            yield session