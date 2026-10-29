"""Seed the three settings that name the credential variables of the GitHub Action

Revision ID: 0004_seed_credential_names
Revises: 0003_seed_catalog
Create Date: 2026-10-29

GR-24 added these settings. The rows are frozen. A test compares all org rows with the catalog.
"""

from alembic import op
from sqlalchemy import text

revision = "0004_seed_credential_names"
down_revision = "0003_seed_catalog"
branch_labels = None
depends_on = None


def _migrating(connection) -> None:
    connection.execute(
        text(
            "SELECT set_config('veil.actor', 'migration 0004_seed_credential_names', true)"
        )
    )
    connection.execute(text("SELECT set_config('veil.migrating', 'on', true)"))


def _rows() -> list[tuple[str, str]]:
    return [
        ("jira_email_env", '"JIRA_EMAIL"'),
        ("jira_token_env", '"JIRA_API_TOKEN"'),
        ("openai_key_env", '"OPENAI_API_KEY"'),
    ]


def upgrade() -> None:
    connection = op.get_bind()
    _migrating(connection)
    connection.execute(
        text(
            "INSERT INTO settings (scope, key, value, type, min_value, max_value) "
            "VALUES ('org', :key, CAST(:value AS jsonb), 'str', NULL, NULL)"
        ),
        [{"key": key, "value": value} for key, value in _rows()],
    )


def downgrade() -> None:
    connection = op.get_bind()
    _migrating(connection)
    connection.execute(
        text("DELETE FROM settings WHERE scope = 'org' AND key = ANY(:keys)"),
        {"keys": [key for key, _ in _rows()]},
    )
