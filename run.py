import os

from app import create_app

# Локальная проверка: http://127.0.0.1:5000
# В сети: HOST=0.0.0.0, проброс порта на роутере при необходимости.
HOST = "0.0.0.0"
PORT = 5000
DEBUG = False
USE_RELOADER = os.environ.get("ROLEPLAY_TRAINER_RELOAD", "0").strip().lower() in (
    "1",
    "true",
    "yes",
)

app = create_app()

if __name__ == "__main__":
    print(f"local:  http://127.0.0.1:{PORT}")
    print(f"reload: {'on' if USE_RELOADER else 'off'}  debug: {'on' if DEBUG else 'off'}")
    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG,
        use_reloader=USE_RELOADER,
        use_debugger=DEBUG,
        threaded=True,
    )
