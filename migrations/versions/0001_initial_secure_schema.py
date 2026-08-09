"""Initial portable schema and persistent auth throttle."""

from alembic import op
import sqlalchemy as sa

revision = "0001_secure"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("users"):
        op.create_table(
            "users",
            sa.Column("user_id", sa.Integer(), primary_key=True),
            sa.Column("login", sa.String(64), nullable=False, unique=True),
            sa.Column("password", sa.String(255), nullable=False),
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("nickname", sa.String(32), nullable=True, unique=True),
            sa.Column("avatar", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("last_login_at", sa.DateTime(), nullable=False),
        )
    if not inspector.has_table("scenarios"):
        op.create_table(
            "scenarios",
            sa.Column("scenario_id", sa.Integer(), primary_key=True),
            sa.Column("owner_user_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("file_name", sa.String(64), nullable=False, unique=True),
            sa.Column("format_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.user_id"]),
        )
        op.create_index("ix_scenarios_owner_user_id", "scenarios", ["owner_user_id"])
    if not inspector.has_table("auth_attempts"):
        op.create_table(
            "auth_attempts",
            sa.Column("attempt_id", sa.Integer(), primary_key=True),
            sa.Column("action", sa.String(16), nullable=False),
            sa.Column("identity_hash", sa.String(64), nullable=False),
            sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("window_started_at", sa.DateTime(), nullable=False),
            sa.Column("blocked_until", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("action", "identity_hash", name="uq_auth_attempt_bucket"),
        )
        op.create_index("ix_auth_attempt_updated", "auth_attempts", ["updated_at"])


def downgrade():
    # Intentionally non-destructive. Rollback requires an explicit, reviewed migration.
    pass
