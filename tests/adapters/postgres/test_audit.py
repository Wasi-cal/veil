import pytest
from sqlalchemy.exc import DBAPIError

from tests.support.postgres_sql import (
    add_repo,
    read,
    run,
    set_org,
    value_of,
)
from veil.engine import Settings, settings_catalog

AUDIT = "SELECT actor, action, scope, key, old_value, new_value, at FROM settings_audit WHERE actor = :actor ORDER BY id"


def test_the_seed_is_in_the_audit_trail_with_the_migration_as_the_actor(engine):
    [(count,)] = read(
        engine,
        "SELECT count(*) FROM settings_audit WHERE actor = 'migration 0003_seed_catalog' AND action = 'insert'",
    )

    assert count == len(settings_catalog())


def test_an_update_records_who_when_the_old_value_and_the_new_value(engine):
    set_org(engine, "step_cap", 30, actor="alice")

    [row] = read(engine, AUDIT, actor="alice")
    assert row[:6] == ("alice", "update", "org", "step_cap", Settings().step_cap, 30)
    assert row[6] is not None


def test_an_insert_and_a_delete_are_recorded_too(engine):
    add_repo(engine, "cheap_model", "repo-model", actor="bob")
    run(
        engine,
        "DELETE FROM settings WHERE scope = 'repo:acme/app' AND key = 'cheap_model'",
        actor="bob",
    )

    rows = read(engine, AUDIT, actor="bob")
    assert [r[:6] for r in rows] == [
        ("bob", "insert", "repo:acme/app", "cheap_model", None, "repo-model"),
        ("bob", "delete", "repo:acme/app", "cheap_model", "repo-model", None),
    ]


@pytest.mark.parametrize("actor", [None, ""])
def test_a_write_with_no_actor_is_refused_and_changes_nothing(engine, actor):
    with pytest.raises(DBAPIError, match="actor"):
        set_org(engine, "step_cap", 30, actor=actor)

    assert value_of(engine, "org", "step_cap") == 25


def test_a_refused_write_leaves_no_audit_row(engine):
    with pytest.raises(DBAPIError):
        set_org(engine, "step_cap", 500, actor="carol")

    assert read(engine, AUDIT, actor="carol") == []


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE settings_audit SET actor = 'mallory'",
        "DELETE FROM settings_audit",
        "TRUNCATE settings_audit",
    ],
)
def test_nobody_can_change_the_audit_trail(engine, sql):
    with pytest.raises(DBAPIError, match="audit"):
        run(engine, sql)


def test_each_write_adds_one_to_the_version(engine):
    [(before,)] = read(engine, "SELECT version FROM settings_version")

    set_org(engine, "step_cap", 30)
    add_repo(engine, "cheap_model", "m")

    [(after,)] = read(engine, "SELECT version FROM settings_version")
    assert after == before + 2


def test_a_write_that_changes_nothing_leaves_no_audit_row_and_no_new_version(engine):
    [(before,)] = read(engine, "SELECT version FROM settings_version")

    set_org(engine, "step_cap", Settings().step_cap, actor="dave")

    assert read(engine, AUDIT, actor="dave") == []
    [(after,)] = read(engine, "SELECT version FROM settings_version")
    assert after == before


def test_a_change_of_the_bounds_by_a_migration_is_in_the_audit_trail(engine):
    run(
        engine,
        "UPDATE settings SET max_value = 200 WHERE scope = 'org' AND key = 'step_cap'",
        actor="migration test",
        migrating=True,
    )

    [row] = read(engine, AUDIT, actor="migration test")
    assert row[:4] == ("migration test", "update", "org", "step_cap")
