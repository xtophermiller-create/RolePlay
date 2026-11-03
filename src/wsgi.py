from __future__ import annotations

from app import create_app

# единственная точка входа для gunicorn
app = create_app()
