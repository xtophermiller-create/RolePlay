"""Guest users: is_guest flag (TTL cleanup uses created_at)."""

from alembic import op
import sqlalchemy as sa

revision = "0006_guest_users"
down_revision = "0005_play_ready"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "is_guest" in cols:
        return
    op.add_column(
        "users",
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "is_guest" not in cols:
        return
    op.drop_column("users", "is_guest")
