"""Stub: ready_at на rp_sessions (уже мог быть применён вручную / stamp).

revision id совпадает с тем, что уже в alembic_version на части окружений.
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_session_ready_at"
down_revision = "0007_scenario_delete_history"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("rp_sessions"):
        return
    cols = {c["name"] for c in inspector.get_columns("rp_sessions")}
    if "ready_at" not in cols:
        op.add_column(
            "rp_sessions",
            sa.Column("ready_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("rp_sessions"):
        return
    cols = {c["name"] for c in inspector.get_columns("rp_sessions")}
    if "ready_at" in cols:
        op.drop_column("rp_sessions", "ready_at")
