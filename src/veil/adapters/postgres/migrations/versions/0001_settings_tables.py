"""The settings table, the audit table and the version counter

Revision ID: 0001_settings_tables
Revises:
Create Date: 2026-10-29
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_settings_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("min_value", sa.Numeric(), nullable=True),
        sa.Column("max_value", sa.Numeric(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("scope", "key"),
        sa.CheckConstraint(
            "type IN ('int', 'str', 'bool', 'list', 'map')", name="type_is_known"
        ),
        sa.CheckConstraint(
            "(type = 'int' AND jsonb_typeof(value) = 'number') "
            "OR (type = 'str' AND jsonb_typeof(value) = 'string') "
            "OR (type = 'bool' AND jsonb_typeof(value) = 'boolean') "
            "OR (type = 'list' AND jsonb_typeof(value) = 'array') "
            "OR (type = 'map' AND jsonb_typeof(value) = 'object')",
            name="value_matches_type",
        ),
        sa.CheckConstraint(
            "type <> 'int' OR (min_value IS NOT NULL AND max_value IS NOT NULL)",
            name="a_number_has_bounds",
        ),
        sa.CheckConstraint(
            "type <> 'int' OR jsonb_typeof(value) <> 'number' OR ("
            "(value #>> '{}')::numeric = trunc((value #>> '{}')::numeric) "
            "AND (value #>> '{}')::numeric BETWEEN min_value AND max_value)",
            name="a_number_is_whole_and_in_bounds",
        ),
    )
    op.create_table(
        "settings_audit",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "action IN ('insert', 'update', 'delete')", name="action_is_known"
        ),
    )
    op.create_table(
        "settings_version",
        sa.Column("id", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "version", sa.BigInteger(), server_default=sa.text("0"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id", name="single_row"),
    )
    op.execute("INSERT INTO settings_version (id, version) VALUES (true, 0)")


def downgrade() -> None:
    op.drop_table("settings_version")
    op.drop_table("settings_audit")
    op.drop_table("settings")
