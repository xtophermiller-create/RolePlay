from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text, Integer, Identity, String, DateTime, Boolean
from ...app import db
from .mixin import TimestampMixin

USER_LENGTH = {
    'MIN_LOGIN': 3,
    'MAX_LOGIN': 32,
    'MIN_PASSWORD': 9,
    'MAX_PASSWORD': 32,
    'MIN_NICKNAME': 3,
    'MAX_NICKNAME': 32,
    'MAX_AVATAR': 32,
}


class User(db.Model, TimestampMixin):
    ''' Схема таблицы users '''
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    login: Mapped[str] = mapped_column(String(USER_LENGTH['MAX_LOGIN']), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)

    nickname: Mapped[str | None] = mapped_column(String(USER_LENGTH['MAX_NICKNAME']), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(USER_LENGTH['MAX_AVATAR']), nullable=True)

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))

    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))