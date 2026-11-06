from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from app.app import db

ROOT_DIR = Path(__file__).resolve().parent
DB_DIR = ROOT_DIR / "app" / "domain" / "db"


def execute_sql_file(connection, path: Path) -> None:
    ''' Выполнить SQL-файл через существующее соединение '''
    sql = path.read_text(encoding="utf-8")
    connection.exec_driver_sql(sql)


def main() -> None:
    ''' Первоначальная настройка схемы PostgreSQL '''
    load_dotenv(ROOT_DIR.parent / ".env")

    database_url = os.environ["DATABASE_OWNER_URL"]
    engine = create_engine(database_url)

    try:
        with engine.begin() as connection:
            # execute_sql_file(connection, DB_DIR / "triggers_drop.sql")
            # db.metadata.drop_all(bind=connection)
            # execute_sql_file(connection, DB_DIR / "functions_drop.sql")
            execute_sql_file(connection, DB_DIR / "recreation_session.sql")
            execute_sql_file(connection, DB_DIR / "functions.sql")
            db.metadata.create_all(bind=connection)
            execute_sql_file(connection, DB_DIR / "triggers.sql")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
