from __future__ import annotations

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

DEFAULT_DOCUMENT = {
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