from __future__ import annotations

from ...app import db

from sqlalchemy import Identity, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class SessionObserver(db.Model):
    __table_args__ = (UniqueConstraint('session_id', 'user_id'),)
    __tablename__ = 'session_observers'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    session_id: Mapped[int] = mapped_column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)