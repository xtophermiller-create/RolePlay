from __future__ import annotations

from sqlalchemy import MetaData, Table

metadata = MetaData()
users = None


def init_users(engine):
    ''' Зеркалим схему users из db '''
    global users

    users = Table(
        'users',
        metadata,
        autoload_with=engine,
    )