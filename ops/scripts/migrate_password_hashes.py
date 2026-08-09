"""Hash every legacy plaintext password in the configured database."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.domain.models import User  # noqa: E402
from app.extensions import db  # noqa: E402
from app.services.auth import hash_password  # noqa: E402


def main() -> int:
    app = create_app()
    with app.app_context():
        changed = 0
        try:
            for user in User.query.yield_per(100):
                if not (user.password or "").startswith(("scrypt:", "pbkdf2:")):
                    user.password = hash_password(user.password)
                    changed += 1
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        print(f"Password migration complete: {changed} account(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
