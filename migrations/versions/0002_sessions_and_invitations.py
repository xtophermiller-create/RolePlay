"""Sessions and temporary invitations."""

from alembic import op
import sqlalchemy as sa

revision = "0002_sessions"
down_revision = "0001_secure"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect = bind.dialect.name

    if inspector.has_table("users"):
        # SQLite не enforce'ит длину VARCHAR; batch_alter ломает FK → users.
        if dialect != "sqlite":
            cols = {c["name"]: c for c in inspector.get_columns("users")}
            nick = cols.get("nickname")
            if nick is not None:
                op.alter_column(
                    "users",
                    "nickname",
                    existing_type=sa.String(length=32),
                    type_=sa.String(length=64),
                    existing_nullable=True,
                )
        op.execute(
            sa.text(
                "UPDATE users SET nickname = login "
                "WHERE nickname IS NULL OR nickname = ''"
            )
        )

    # re-inspect after possible alters
    inspector = sa.inspect(bind)

    if not inspector.has_table("rp_sessions"):
        op.create_table(
            "rp_sessions",
            sa.Column("session_id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(16), nullable=False),
            sa.Column("host_user_id", sa.Integer(), nullable=False),
            sa.Column("scenario_id", sa.Integer(), nullable=False),
            sa.Column("scenario_title", sa.String(200), nullable=False),
            sa.Column("scenario_snapshot", sa.Text(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="lobby"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["host_user_id"], ["users.user_id"]),
            sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"]),
            sa.UniqueConstraint("code"),
        )
        op.create_index("ix_rp_sessions_code", "rp_sessions", ["code"])
        op.create_index("ix_rp_sessions_host_user_id", "rp_sessions", ["host_user_id"])
        op.create_index("ix_rp_sessions_scenario_id", "rp_sessions", ["scenario_id"])
        op.create_index("ix_rp_sessions_status", "rp_sessions", ["status"])

    if not inspector.has_table("session_participants"):
        op.create_table(
            "session_participants",
            sa.Column("participant_id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(16), nullable=True),
            sa.Column("joined_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["session_id"], ["rp_sessions.session_id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.UniqueConstraint("session_id", "user_id", name="uq_session_user"),
        )
        op.create_index(
            "ix_session_participants_session_id", "session_participants", ["session_id"]
        )
        op.create_index(
            "ix_session_participants_user_id", "session_participants", ["user_id"]
        )
        op.create_index(
            "ix_session_role", "session_participants", ["session_id", "role"]
        )

    if not inspector.has_table("session_invitations"):
        op.create_table(
            "session_invitations",
            sa.Column("invite_id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("from_user_id", sa.Integer(), nullable=False),
            sa.Column("to_user_id", sa.Integer(), nullable=False),
            sa.Column("to_handle", sa.String(64), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["session_id"], ["rp_sessions.session_id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["from_user_id"], ["users.user_id"]),
            sa.ForeignKeyConstraint(["to_user_id"], ["users.user_id"]),
        )
        op.create_index(
            "ix_session_invitations_session_id", "session_invitations", ["session_id"]
        )
        op.create_index(
            "ix_session_invitations_from_user_id",
            "session_invitations",
            ["from_user_id"],
        )
        op.create_index(
            "ix_session_invitations_to_user_id", "session_invitations", ["to_user_id"]
        )
        op.create_index(
            "ix_session_invitations_expires_at", "session_invitations", ["expires_at"]
        )


def downgrade():
    # Intentionally non-destructive.
    pass
