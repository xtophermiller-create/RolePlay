""" Базовая модель USER, может быть использована в любых типовых приложениях """


from datetime import datetime, timezone
from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)

    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_guest = db.Column(db.Boolean, nullable=False, default=False)

    nickname = db.Column(db.String(64), unique=True, nullable=True)
    avatar = db.Column(db.String(256), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    last_login_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)