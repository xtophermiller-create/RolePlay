"""Выровнять схему сессий под текущие модели (модели — истина).

- rp_sessions: убрать updated_at (модель его не пишет → 500 на create)
- session_participants → rp_session_participants
- убрать presence-поля, которых нет в RpSessionParticipant
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_align_sessions_to_models"
down_revision = "0008_session_ready_at"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("rp_sessions"):
        cols = {c["name"] for c in inspector.get_columns("rp_sessions")}
        if "updated_at" in cols:
            with op.batch_alter_table("rp_sessions") as batch:
                batch.drop_column("updated_at")

    inspector = sa.inspect(bind)
    if inspector.has_table("session_participants") and not inspector.has_table(
        "rp_session_participants"
    ):
        op.rename_table("session_participants", "rp_session_participants")

    inspector = sa.inspect(bind)
    if inspector.has_table("rp_session_participants"):
        cols = {c["name"] for c in inspector.get_columns("rp_session_participants")}
        drop_cols = [name for name in ("joined_at", "last_seen_at", "away_at") if name in cols]
        if "is_ready" not in cols:
            op.add_column(
                "rp_session_participants",
                sa.Column(
                    "is_ready",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
            cols.add("is_ready")
        if drop_cols:
            with op.batch_alter_table("rp_session_participants") as batch:
                for name in drop_cols:
                    batch.drop_column(name)
        # role в модели NOT NULL
        cols = {
            c["name"]: c for c in sa.inspect(bind).get_columns("rp_session_participants")
        }
        role = cols.get("role")
        if role is not None and role.get("nullable", True):
            op.execute(
                sa.text(
                    "UPDATE rp_session_participants "
                    "SET role = 'observer' WHERE role IS NULL OR role = ''"
                )
            )
            with op.batch_alter_table("rp_session_participants") as batch:
                batch.alter_column(
                    "role",
                    existing_type=sa.String(length=16),
                    nullable=False,
                    server_default="observer",
                )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("rp_session_participants") and not inspector.has_table(
        "session_participants"
    ):
        with op.batch_alter_table("rp_session_participants") as batch:
            batch.add_column(sa.Column("joined_at", sa.DateTime(), nullable=True))
            batch.add_column(sa.Column("last_seen_at", sa.DateTime(), nullable=True))
            batch.add_column(sa.Column("away_at", sa.DateTime(), nullable=True))
        op.execute(
            sa.text(
                "UPDATE rp_session_participants "
                "SET joined_at = CURRENT_TIMESTAMP WHERE joined_at IS NULL"
            )
        )
        op.rename_table("rp_session_participants", "session_participants")

    inspector = sa.inspect(bind)
    if inspector.has_table("rp_sessions"):
        cols = {c["name"] for c in inspector.get_columns("rp_sessions")}
        if "updated_at" not in cols:
            op.add_column(
                "rp_sessions",
                sa.Column("updated_at", sa.DateTime(), nullable=True),
            )
            op.execute(
                sa.text(
                    "UPDATE rp_sessions SET updated_at = created_at "
                    "WHERE updated_at IS NULL"
                )
            )
            with op.batch_alter_table("rp_sessions") as batch:
                batch.alter_column(
                    "updated_at",
                    existing_type=sa.DateTime(),
                    nullable=False,
                )
