"""Allow deleting scenarios while preserving session history."""

from alembic import op
import sqlalchemy as sa


revision = "0007_scenario_delete_history"
down_revision = "0006_guest_users"
branch_labels = None
depends_on = None


_FK_NAME = "fk_rp_sessions_scenario_id_scenarios"


def _scenario_foreign_key(inspector):
    for foreign_key in inspector.get_foreign_keys("rp_sessions"):
        if (
            foreign_key.get("referred_table") == "scenarios"
            and foreign_key.get("constrained_columns") == ["scenario_id"]
        ):
            return foreign_key
    return None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("rp_sessions"):
        return

    foreign_key = _scenario_foreign_key(inspector)
    if bind.dialect.name == "sqlite":
        naming_convention = {
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        }
        with op.batch_alter_table(
            "rp_sessions",
            recreate="always",
            naming_convention=naming_convention,
        ) as batch:
            if foreign_key:
                batch.drop_constraint(
                    foreign_key.get("name") or _FK_NAME,
                    type_="foreignkey",
                )
            batch.alter_column(
                "scenario_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
            batch.create_foreign_key(
                _FK_NAME,
                "scenarios",
                ["scenario_id"],
                ["scenario_id"],
                ondelete="SET NULL",
            )
        return

    if foreign_key and foreign_key.get("name"):
        op.drop_constraint(
            foreign_key["name"],
            "rp_sessions",
            type_="foreignkey",
        )
    op.alter_column(
        "rp_sessions",
        "scenario_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_foreign_key(
        _FK_NAME,
        "rp_sessions",
        "scenarios",
        ["scenario_id"],
        ["scenario_id"],
        ondelete="SET NULL",
    )


def downgrade():
    # Restoring NOT NULL would destroy or rewrite preserved session history.
    pass
