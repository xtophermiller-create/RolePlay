from __future__ import annotations

from app import create_app

HOST = "127.0.0.1"
PORT = 5000

app = create_app()

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, threaded=True, debug=True)
