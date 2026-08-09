"""Play: is_ready, away_at (active grace), session abort_at fallback."""

from alembic import op
import sqlalchemy as sa

revision = "0005_play_ready"
down_revision = "0004_session_history"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("session_participants"):
        cols = {c["name"] for c in inspector.get_columns("session_participants")}
        if "is_ready" not in cols:
            op.add_column(
                "session_participants",
                sa.Column(
                    "is_ready",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
        if "away_at" not in cols:
            op.add_column(
                "session_participants",
                sa.Column("away_at", sa.DateTime(), nullable=True),
            )

    if inspector.has_table("rp_sessions"):
        cols = {c["name"] for c in inspector.get_columns("rp_sessions")}
        if "abort_at" not in cols:
            op.add_column(
                "rp_sessions",
                sa.Column("abort_at", sa.DateTime(), nullable=True),
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("session_participants"):
        cols = {c["name"] for c in inspector.get_columns("session_participants")}
        if "away_at" in cols:
            op.drop_column("session_participants", "away_at")
        if "is_ready" in cols:
            op.drop_column("session_participants", "is_ready")
    if inspector.has_table("rp_sessions"):
        cols = {c["name"] for c in inspector.get_columns("rp_sessions")}
        if "abort_at" in cols:
            op.drop_column("rp_sessions", "abort_at")
