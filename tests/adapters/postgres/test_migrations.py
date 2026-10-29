import os
import subprocess
import sys
import threading

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from veil.adapters.postgres.migrate import apply_migrations, revert_migrations
from veil.adapters.postgres.orm.base import Base
from veil.engine import settings_catalog

TABLES = {"settings", "settings_audit", "settings_version"}


def tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_all_migrations_apply_to_an_empty_database(empty_engine):
    assert tables(empty_engine) == set()

    apply_migrations(empty_engine)

    assert tables(empty_engine) == TABLES


def test_applying_the_migrations_again_changes_nothing(empty_engine):
    apply_migrations(empty_engine)
    apply_migrations(empty_engine)

    assert tables(empty_engine) == TABLES


def test_the_seed_is_the_whole_catalog_with_its_defaults_and_bounds(engine):
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT key, value, type, min_value, max_value FROM settings WHERE scope = 'org' ORDER BY key"
            )
        ).all()

    expected = sorted(
        (
            e.key,
            e.default if not isinstance(e.default, tuple) else list(e.default),
            e.value_type,
            e.minimum,
            e.maximum,
        )
        for e in settings_catalog()
    )
    seeded = [
        (
            key,
            value,
            kind,
            None if low is None else int(low),
            None if high is None else int(high),
        )
        for key, value, kind, low, high in rows
    ]
    assert seeded == expected


def test_the_orm_models_match_the_migrated_tables(engine):
    with engine.connect() as connection:
        differences = compare_metadata(
            MigrationContext.configure(connection), Base.metadata
        )

    assert differences == []


def test_the_migrations_can_be_reverted_to_an_empty_database(empty_engine):
    apply_migrations(empty_engine)

    revert_migrations(empty_engine)

    assert tables(empty_engine) == set()


def test_two_deployments_that_migrate_at_the_same_time_both_succeed(empty_engine):
    errors = []

    def migrate():
        try:
            apply_migrations(empty_engine)
        except Exception as failure:  # noqa: BLE001
            errors.append(failure)

    threads = [threading.Thread(target=migrate) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert tables(empty_engine) == TABLES


def test_the_migration_program_applies_the_migrations_from_a_url_in_a_variable(
    empty_engine,
):
    url = empty_engine.url.render_as_string(hide_password=False)

    result = subprocess.run(
        [sys.executable, "-m", "veil.adapters.postgres.migrate"],
        env={**os.environ, "VEIL_DATABASE_URL": url},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert tables(empty_engine) == TABLES


def test_the_migration_program_fails_with_a_clear_message_when_there_is_no_url():
    env = {k: v for k, v in os.environ.items() if k != "VEIL_DATABASE_URL"}

    result = subprocess.run(
        [sys.executable, "-m", "veil.adapters.postgres.migrate"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "VEIL_DATABASE_URL" in result.stderr
