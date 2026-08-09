"""Participant last_seen_at for lobby presence heartbeat."""

from alembic import op
import sqlalchemy as sa

revision = "0003_presence"
down_revision = "0002_sessions"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("session_participants"):
        return
    cols = {c["name"] for c in inspector.get_columns("session_participants")}
    if "last_seen_at" in cols:
        return
    op.add_column(
        "session_participants",
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE session_participants "
            "SET last_seen_at = joined_at "
            "WHERE last_seen_at IS NULL"
        )
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("session_participants"):
        return
    cols = {c["name"] for c in inspector.get_columns("session_participants")}
    if "last_seen_at" not in cols:
        return
    op.drop_column("session_participants", "last_seen_at")
