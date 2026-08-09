from datetime import datetime, timezone
from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class AuthAttempt(db.Model):
    __tablename__ = "auth_attempts"

    attempt_id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(16), nullable=False)
    identity_hash = db.Column(db.String(64), nullable=False)
    failures = db.Column(db.Integer, nullable=False, default=0)
    window_started_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    blocked_until = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        db.UniqueConstraint("action", "identity_hash", name="uq_auth_attempt_bucket"),
        db.Index("ix_auth_attempt_updated", "updated_at"),
    )
