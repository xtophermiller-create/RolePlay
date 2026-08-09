""" Базовая модель сценария, с версией для обновлений db """


from datetime import datetime, timezone
from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class Scenario(db.Model):
    __tablename__ = "scenarios"

    scenario_id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)

    title = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), unique=True, nullable=False)

    format_version = db.Column(db.Integer, nullable=False, default=1)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)