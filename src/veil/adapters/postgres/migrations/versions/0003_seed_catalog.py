"""Seed one org row for every setting of the catalog, with its default and its bounds

Revision ID: 0003_seed_catalog
Revises: 0002_guards_and_audit
Create Date: 2026-10-29

The rows are the catalog as it was when this migration was written. They are frozen. A later change of the
catalog needs a new migration. A test compares the rows with the catalog and fails when they differ.
Each row is an org row. So a repo can only tighten the default, and a locked value stays locked.
"""

from alembic import op
from sqlalchemy import text

revision = "0003_seed_catalog"
down_revision = "0002_guards_and_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    rows = [
        ("cheap_model", '"gpt-6-luna"', "str", None, None),
        ("strong_model", '"gpt-6.1-terra"', "str", None, None),
        ("max_attempts", "2", "int", 1, 2),
        ("step_cap", "25", "int", 1, 100),
        ("diff_limit", "200", "int", 0, 2000),
        ("tool_result_max_bytes", "8192", "int", 256, 65536),
        ("read_file_max_lines", "300", "int", 1, 2000),
        ("search_max_matches", "50", "int", 1, 500),
        ("explanation_max_sentences", "3", "int", 1, 10),
        ("extra_refused_read_patterns", "[]", "list", None, None),
        ("token_ceiling", "100000", "int", 1, 5000000),
        ("model_calls_per_minute", "20", "int", 1, 600),
        ("shared_pr_max", "10", "int", 1, 50),
        ("branch_prefix", '"gozu/fix-"', "str", None, None),
        (
            "severity_map",
            '{"BLOCKER": "high", "CRITICAL": "high", "MAJOR": "medium", "MINOR": "low", "INFO": "low", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}',
            "map",
            None,
            None,
        ),
        ("eligible_label", '"veil-eligible"', "str", None, None),
        ("failed_fix_label", '"veil-failed-fix"', "str", None, None),
        ("in_review_status", '"In Review"', "str", None, None),
        ("jira_site_url", '""', "str", None, None),
        ("jira_project_keys", "[]", "list", None, None),
        ("repos_allow", "[]", "list", None, None),
        ("repos_deny", "[]", "list", None, None),
        ("schedule_enabled", "false", "bool", None, None),
        ("schedule_cron", '"0 6 * * *"', "str", None, None),
        ("on_demand_enabled", "true", "bool", None, None),
        ("event_enabled", "true", "bool", None, None),
        ("quiet_window_minutes", "10", "int", 0, 120),
        ("run_timeout_minutes", "60", "int", 1, 240),
        ("heartbeat_seconds", "120", "int", 10, 600),
        ("max_concurrent_runs", "3", "int", 1, 20),
        ("checkout_sweep_minutes", "60", "int", 10, 1440),
        ("cache_settings_ttl_seconds", "60", "int", 1, 86400),
        ("cache_jira_metadata_ttl_seconds", "300", "int", 1, 86400),
        ("cache_repo_list_ttl_seconds", "600", "int", 1, 86400),
    ]
    connection = op.get_bind()
    connection.execute(
        text("SELECT set_config('veil.actor', 'migration 0003_seed_catalog', true)")
    )
    connection.execute(text("SELECT set_config('veil.migrating', 'on', true)"))
    connection.execute(
        text(
            "INSERT INTO settings (scope, key, value, type, min_value, max_value) "
            "VALUES ('org', :key, CAST(:value AS jsonb), :type, :minimum, :maximum)"
        ),
        [
            {"key": key, "value": value, "type": kind, "minimum": low, "maximum": high}
            for key, value, kind, low, high in rows
        ],
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        text("SELECT set_config('veil.actor', 'migration 0003_seed_catalog', true)")
    )
    connection.execute(text("SELECT set_config('veil.migrating', 'on', true)"))
    connection.execute(text("DELETE FROM settings WHERE scope = 'org'"))
