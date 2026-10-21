from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[4] / 'log'


def configurate_logging(
    level: int = logging.INFO,
) -> None:
    ''' Глобальная настройка логирования приложения '''

    LOG_PATH.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S",
        format='[%(asctime)s:%(msecs)03d] % (module)10s:%(lineno)-3d %(levelname)-7s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            TimedRotatingFileHandler(
                filename=LOG_PATH / "roleplay.log",
                when="midnight",
                interval=1,
                backupCount=14,
                encoding="utf-8",
            ),
        ],
    )














from __future__ import annotations

import logging


def configurate_logging(level=logging.INFO):
    ''' Глобальные настройки логов '''
    logging.basicConfig(
        level=level,
        datefmt='%Y-%m-%d %H:%M:%S',
        format='[%(asctime)s:%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s',
    )