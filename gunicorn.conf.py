from pathlib import Path

wsgi_app = "wsgi:app"
chdir = str(Path(__file__).resolve().parent / "src")

# строго один процесс: комнаты живут в его памяти
workers = 1
# каждое WebSocket соединение (открытая страница комнаты) занимает поток целиком,
# поэтому потоков нужно с запасом больше, чем одновременно открытых страниц комнат
threads = 100

bind = "127.0.0.1:8000"

timeout = 120
