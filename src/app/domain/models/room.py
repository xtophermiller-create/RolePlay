from __future__ import annotations

from sqlalchemy import Identity, text, CheckConstraint, Boolean, Integer, ForeignKey, String
from .mixin import TimestampMixin
from ...app import db
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY, array

ROOM_LENGTH = {
    'MAX_STATUS': 16,
    'MIN_CODE': 8,
    'MAX_CODE': 8
}


class Room(db.Model, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint(
            '(actor1_id IS NOT NULL OR NOT ready1) '
            'AND (actor2_id IS NOT NULL OR NOT ready2)',
            name='rooms_ready_check',
        ),
        CheckConstraint(
            'room_roles_ok(owner_id, player_ids, actor1_id, actor2_id, observer_ids)',
            name='rooms_roles_check',
        ),
        CheckConstraint(
            "((status)::text = 'lobby'::text AND session_id IS NULL) "
            "OR ((status)::text = 'in_session'::text AND session_id IS NOT NULL)",
            name='rooms_session_link_check',
        ),
        CheckConstraint(
            "status::text = ANY (ARRAY['lobby'::character varying, 'in_session'::character varying]::text[])",
            name='rooms_status_check',
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(ROOM_LENGTH['MAX_CODE']), nullable=False, unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name='room_owner_id_fkey'), nullable=False)
    scenario_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('scenarios.id', name='room_scenario_id_fkey', ondelete='SET NULL'), nullable=True)
    session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('sessions.id', name='room_session_id_fkey', ondelete='SET NULL'), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(ROOM_LENGTH['MAX_STATUS']), nullable=False, server_default=text("'lobby'"))
    player_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, server_default=text("'{}'::integer[]"))
    actor1_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('users.id', name='actor1_user_id_fkey', ondelete='SET NULL'), nullable=True)
    actor2_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('users.id', name='actor2_user_id_fkey', ondelete='SET NULL'), nullable=True)
    observer_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, server_default=text("'{}'::integer[]"))
    ready1: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    ready2: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))