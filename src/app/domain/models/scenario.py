from __future__ import annotations

import json
from sqlalchemy import Identity, text, CheckConstraint, Integer, ForeignKey
from .mixin import TimestampMixin, pg_default
from ...app import db
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

SCENARIO_LENGTH = {
    'MAX_TITLE': 64,
    'MAX_ACTOR1': 32,
    'MAX_ACTOR2': 32,
    'MAX_TARGET1': 256,
    'MAX_TARGET2': 256,
    'MAX_CONTEXT1': 512,
    'MAX_CONTEXT2': 512,
}

SCENARIO_DEFAULT = {
    'VERSION': 2,
    'TITLE': 'Unnamed scenario',
    'ACTOR1': 'Role 1',
    'ACTOR2': 'Role 2'
}

SCENARIO_TYPES = {
    'DOC': {
        'type': 'doc',
        'content': []
    },

    'HEADING': {
        'type': 'heading',
        'content': ''
    },
    'PARAGRAPH': {
        'type': 'paragraph',
        'content': []
    },
    'IMAGE': {
        'type': 'image',
        'content': ''
    },
    'NUM_LIST': {
        'type': 'numList',
        'content': []
    },
    'MARKED_LIST': {
        'type': 'markedList',
        'content': []
    },
    'SECTION': {
        'type': 'section',
        'content': []
    },

    'TEXT': {
        'type': 'text',
        'content': ''
    },
    'HARD_BREAK': {
        'type': 'hardBreak',
        'content': None
    }
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

    title: Mapped[str] = mapped_column(String(SCENARIO_LENGTH['MAX_TITLE']), nullable=False, server_default=text(pg_default(SCENARIO_DEFAULT['TITLE'])))
    format_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text(str(SCENARIO_DEFAULT['VERSION'])))

    actor1: Mapped[str] = mapped_column(String(SCENARIO_LENGTH['MAX_ACTOR1']), nullable=False, server_default=text(pg_default(SCENARIO_DEFAULT['ACTOR1'])))
    actor2: Mapped[str] = mapped_column(String(SCENARIO_LENGTH['MAX_ACTOR2']), nullable=False, server_default=text(pg_default(SCENARIO_DEFAULT['ACTOR2'])))
    target1: Mapped[str | None] = mapped_column(String(SCENARIO_LENGTH['MAX_TARGET1']), nullable=True)
    target2: Mapped[str | None] = mapped_column(String(SCENARIO_LENGTH['MAX_TARGET2']), nullable=True)
    context1: Mapped[str | None] = mapped_column(String(SCENARIO_LENGTH['MAX_CONTEXT1']), nullable=True)
    context2: Mapped[str | None] = mapped_column(String(SCENARIO_LENGTH['MAX_CONTEXT2']), nullable=True)
    document1: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'" + json.dumps(SCENARIO_TYPES['DOC']) + "'::jsonb"))
    document2: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'" + json.dumps(SCENARIO_TYPES['DOC']) + "'::jsonb"))


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



EXAMPLE2 = {
  "type": "doc",
  "content": [
    {
      "type": "heading",
      "attrs": {
        "level": 1
      },
      "content": [
        {
          "type": "text",
          "text": "SAMPLE"
        }
      ]
    },
    {
      "type": "paragraph",
      "content": [
        {
          "type": "text",
          "text": "SAMPLE"
        },
        {
          "type": "hardBreak"
        }
      ]
    },
    {
      "type": "image",
      "attrs": {
        "src": "SAMPLE.jpg"
      }
    },
    {
      "type": "orderedList",
      "content": [
        {
          "type": "listItem",
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "SAMPLE"
                },
                {
                  "type": "hardBreak"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "bulletList",
      "content": [
        {
          "type": "listItem",
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "SAMPLE"
                },
                {
                  "type": "hardBreak"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "section",
      "content": []
    }
  ]
}