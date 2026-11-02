from __future__ import annotations

from app import create_app
from app.app import socketio
from app.config import env_flag

HOST = "127.0.0.1"
PORT = 5000

app = create_app()

# только для локального запуска; reloader в debug вызывает create_app дважды
if __name__ == "__main__":
    socketio.run(app, host=HOST, port=PORT, debug=env_flag("FLASK_DEBUG"), allow_unsafe_werkzeug=True)
