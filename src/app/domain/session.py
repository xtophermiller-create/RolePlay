from __future__ import annotations

from sqlalchemy import MetaData, Table

metadata = MetaData()
sessions = None


def init_sessions(engine):
    ''' Зеркалим схему sessions из db '''
    global sessions

    sessions = Table(
        'sessions',
        metadata,
        autoload_with=engine,
    )