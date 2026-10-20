from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text, Integer, Identity, String, DateTime, Boolean
from ...app import db
from .mixin import TimestampMixin

LENGTH_LOGIN = 32
LENGTH_PASSWORD = 256
LENGTH_NICKNAME = 32
LENGTH_AVATAR = 32


class User(db.Model, TimestampMixin):
    ''' Схема таблицы users '''
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    login: Mapped[str] = mapped_column(String(LENGTH_LOGIN), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(LENGTH_PASSWORD), nullable=False)

    nickname: Mapped[str | None] = mapped_column(String(LENGTH_NICKNAME), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(LENGTH_AVATAR), nullable=True)

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))

    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))