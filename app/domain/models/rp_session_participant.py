""" Модель участника сессии """


from app.extensions import db


ROLE_ACTOR1 = "actor1"
ROLE_ACTOR2 = "actor2"
ROLE_OBSERVER = "observer"

SESSION_ROLES = (ROLE_ACTOR1, ROLE_ACTOR2, ROLE_OBSERVER)


class RpSessionParticipant(db.Model):
    __tablename__ = "rp_session_participants"

    participant_id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("rp_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    role = db.Column(db.String(16), nullable=False, default=ROLE_OBSERVER)

    session = db.relationship("RpSession", back_populates="participants")

    __table_args__ = (
        db.UniqueConstraint("session_id", "user_id", name="uq_session_user"),
        db.Index("ix_session_role", "session_id", "role"),
    )