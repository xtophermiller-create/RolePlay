from __future__ import annotations

from sqlalchemy import MetaData, Table

metadata = MetaData()
rooms = None


def init_rooms(engine):
    ''' Зеркалим схему rooms из db '''
    global rooms

    rooms = Table(
        'rooms',
        metadata,
        autoload_with=engine,
    )