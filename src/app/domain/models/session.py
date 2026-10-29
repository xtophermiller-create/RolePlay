from __future__ import annotations

from sqlalchemy import Identity, CheckConstraint, Index, Integer, ForeignKey, String, text
from .mixin import TimestampMixin
from .scenario import SCENARIO_LENGTH
from ...app import db
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, array


class Session(db.Model, TimestampMixin):
    __tablename__ = 'sessions'
    __table_args__ = (
        CheckConstraint(
            'NOT (actor1_id = ANY (observer_ids)) '
            'AND NOT (actor2_id = ANY (observer_ids)) '
            'AND array_position(observer_ids, NULL::integer) IS NULL',
            name='sessions_actors_not_observers',
        ),
        CheckConstraint(
            'actor1_id <> actor2_id',
            name='sessions_distinct_actors',
        ),
        CheckConstraint(
            "document1 IS NULL OR jsonb_typeof(document1) = 'object'::text",
            name='sessions_document1_object',
        ),
        CheckConstraint(
            "document2 IS NULL OR jsonb_typeof(document2) = 'object'::text",
            name='sessions_document2_object',
        )
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name='sessions_owner_id_fkey'), nullable=False, index=True)
    actor1_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name='sessions_actor1_id_fkey'), nullable=False, index=True)
    actor2_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name='sessions_actor2_id_fkey'), nullable=False, index=True)
    observer_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, server_default=text("'{}'::integer[]"))

    title: Mapped[str] = mapped_column(String(SCENARIO_LENGTH['MAX_TITLE']), nullable=False)
    format_version: Mapped[int] = mapped_column(Integer, nullable=False)

    actor1: Mapped[str] = mapped_column(String(SCENARIO_LENGTH['MAX_ACTOR1']), nullable=False)
    actor2: Mapped[str] = mapped_column(String(SCENARIO_LENGTH['MAX_ACTOR2']), nullable=False)
    target1: Mapped[str | None] = mapped_column(String(SCENARIO_LENGTH['MAX_TARGET1']), nullable=True)
    target2: Mapped[str | None] = mapped_column(String(SCENARIO_LENGTH['MAX_TARGET2']), nullable=True)
    context1: Mapped[str | None] = mapped_column(String(SCENARIO_LENGTH['MAX_CONTEXT1']), nullable=True)
    context2: Mapped[str | None] = mapped_column(String(SCENARIO_LENGTH['MAX_CONTEXT2']), nullable=True)
    document1: Mapped[dict] = mapped_column(JSONB, nullable=False)
    document2: Mapped[dict] = mapped_column(JSONB, nullable=False)