"""Sessions history: store completion results on rp_sessions."""

from alembic import op
import sqlalchemy as sa

revision = "0004_session_history"
down_revision = "0003_presence"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("rp_sessions"):
        return

    dialect = bind.dialect.name
    cols = {c["name"] for c in inspector.get_columns("rp_sessions")}

    if "result_json" not in cols:
        op.add_column("rp_sessions", sa.Column("result_json", sa.Text(), nullable=True))
    if "result_submitted_by" not in cols:
        op.add_column(
            "rp_sessions",
            sa.Column("result_submitted_by", sa.Integer(), nullable=True),
        )
        if dialect != "sqlite":
            op.create_foreign_key(
                "fk_rp_sessions_result_submitted_by",
                "rp_sessions",
                "users",
                ["result_submitted_by"],
                ["user_id"],
            )
    if "actor1_percent" not in cols:
        op.add_column("rp_sessions", sa.Column("actor1_percent", sa.Float(), nullable=True))
    if "actor2_percent" not in cols:
        op.add_column("rp_sessions", sa.Column("actor2_percent", sa.Float(), nullable=True))
    if "overall_percent" not in cols:
        op.add_column("rp_sessions", sa.Column("overall_percent", sa.Float(), nullable=True))


def downgrade():
    pass
