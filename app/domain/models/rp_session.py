from datetime import datetime, timezone
from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


STATUS_LOBBY = "lobby"
STATUS_STARTED = "started"
STATUS_READY = "ready"
STATUS_FINISHED = "finished"
STATUS_CANCELLED = "cancelled"
# Старые сессии в БД могли остаться с active (= brief / started).
STATUS_ACTIVE = "active"

SESSION_STATUSES = (
    STATUS_LOBBY,
    STATUS_STARTED,
    STATUS_READY,
    STATUS_FINISHED,
    STATUS_CANCELLED,
    STATUS_ACTIVE,
)

# Briefing после старта из лобби; play — когда оба актёра нажали «Готов».
BRIEF_STATUSES = (STATUS_STARTED, STATUS_ACTIVE)
PLAY_STATUSES = (STATUS_READY,)
LIVE_STATUSES = BRIEF_STATUSES + PLAY_STATUSES


class RpSession(db.Model):
    __tablename__ = "rp_sessions"

    session_id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    host_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    scenario_id = db.Column(
        db.Integer,
        db.ForeignKey("scenarios.scenario_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scenario_title = db.Column(db.String(200), nullable=False, default="")
    scenario_snapshot = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default=STATUS_LOBBY, index=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    started_at = db.Column(db.DateTime, nullable=True, default=None)
    ready_at = db.Column(db.DateTime, nullable=True, default=None)
    finished_at = db.Column(db.DateTime, nullable=True, default=None)

    host = db.relationship("User", foreign_keys=[host_user_id])
    scenario = db.relationship("Scenario", foreign_keys=[scenario_id])

    participants = db.relationship(
        "RpSessionParticipant",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
