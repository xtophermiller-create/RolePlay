from __future__ import annotations

import json
from sqlalchemy import Identity, text, CheckConstraint, Integer, ForeignKey
from .mixin import TimestampMixin
from ...app import db
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

LENGTH_TITLE = 64
LENGTH_ACTOR1 = 32
LENGTH_ACTOR2 = 32
LENGTH_TARGET1 = 256
LENGTH_TARGET2 = 256
LENGTH_CONTEXT1 = 512
LENGTH_CONTEXT2 = 512

SCENARIO_VERSION = 2
SCENARIO_TITLE = 'Unnamed scenario'
SCENARIO_ACTOR1 = 'Role 1'
SCENARIO_ACTOR2 = 'Role 2'

DOC_TYPE = {
    'type': 'doc',
    'content': []
}

HEADING_TYPE = {
    'type': 'heading',
    'content': ''
}
PARAGRAPH_TYPE = {
    'type': 'paragraph',
    'content': []
}
IMAGE_TYPE = {
    'type': 'image',
    'content': ''
}
NUM_LIST_TYPE = {
    'type': 'numList',
    'content': []
}
MARKED_LIST_TYPE = {
    'type': 'markedList',
    'content': []
}
SECTION_TYPE = {
    'type': 'section',
    'content': []
}

TEXT_TYPE = {
    'type': 'text',
    'content': ''
}
HARD_BREAK_TYPE = {
    'type': 'hardBreak',
    'content': None
}


class Scenario(db.Model, TimestampMixin):
    ''' Схема таблицы scenarios '''
    __tablename__ = 'scenarios'
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(document1) = 'object'::text",
            name='scenarios_document1_object',
        ),
        CheckConstraint(
            "jsonb_typeof(document2) = 'object'::text",
            name='scenarios_document2_object',
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name='scenario_owner_id_fkey'), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(LENGTH_TITLE), nullable=False, server_default=text(SCENARIO_TITLE))
    format_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text(str(SCENARIO_VERSION)))

    actor1: Mapped[str] = mapped_column(String(LENGTH_ACTOR1), nullable=False, server_default=text(SCENARIO_ACTOR1))
    actor2: Mapped[str] = mapped_column(String(LENGTH_ACTOR2), nullable=False, server_default=text(SCENARIO_ACTOR2))
    target1: Mapped[str | None] = mapped_column(String(LENGTH_TARGET1), nullable=True)
    target2: Mapped[str | None] = mapped_column(String(LENGTH_TARGET2), nullable=True)
    context1: Mapped[str | None] = mapped_column(String(LENGTH_CONTEXT1), nullable=True)
    context2: Mapped[str | None] = mapped_column(String(LENGTH_CONTEXT2), nullable=True)
    document1: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'" + json.dumps(DOC_TYPE) + "'::jsonb"))
    document2: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'" + json.dumps(DOC_TYPE) + "'::jsonb"))


EXAMPLE = {
    'type': 'doc',
    'content': [
        {
            'type': 'heading',
            'content': 'SAMPLE'
        },
        {
            'type': 'paragraph',
            'content': [
                {
                    'type': 'text',
                    'content': 'SAMPLE'
                },
                {
                    'type': 'hardBreak',
                    'content': None
                }
            ]
        },
        {
            'type': 'image',
            'content': 'SAMPLE.jpg'
        },
        {
            'type': 'numList',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {
                            'type': 'text',
                            'content': 'SAMPLE'
                        },
                        {
                            'type': 'hardBreak',
                            'content': None
                        }
                    ]
                }
            ]
        },
        {
            'type': 'markedList',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {
                            'type': 'text',
                            'content': 'SAMPLE'
                        },
                        {
                            'type': 'hardBreak',
                            'content': None
                        }
                    ]
                }
            ]
        },
        {
            'type': 'section',
            'content': [
                # Сюда можно положить ВСЁ что было описано до этого, даже сам section в section положить можно.
                # Но только до 5 уровня, то есть больше чем 5 section вместе с начальным нельзя положить друг в друга.
                # В отдаленном смысле section - это doc внутри doc, по этому в нем можно все, что и в doc.
            ]
        }
    ]
}