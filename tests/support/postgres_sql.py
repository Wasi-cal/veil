"""Small helpers that run SQL against a test database as a named actor."""

import json

from sqlalchemy import text

from veil.adapters.postgres.constants.scopes import ACTOR_VARIABLE

# A migration sets this variable. Only then may the structure of the settings change.
MIGRATING_VARIABLE = "veil.migrating"


def run(engine, sql, actor="tester", migrating=False, **params):
    """Run one statement in one transaction as the given actor. No actor means none is set.

    With migrating=True the transaction says that it is a migration.
    """
    with engine.begin() as connection:
        if actor is not None:
            connection.execute(
                text("SELECT set_config(:name, :actor, true)"),
                {"name": ACTOR_VARIABLE, "actor": actor},
            )
        if migrating:
            connection.execute(
                text("SELECT set_config(:name, 'on', true)"),
                {"name": MIGRATING_VARIABLE},
            )
        return connection.execute(text(sql), params)


def read(engine, sql, **params):
    with engine.connect() as connection:
        return connection.execute(text(sql), params).all()


def set_org(engine, key, value, actor="tester"):
    run(
        engine,
        "UPDATE settings SET value = CAST(:value AS jsonb) WHERE scope = 'org' AND key = :key",
        actor=actor,
        key=key,
        value=json.dumps(value),
    )


def value_of(engine, scope, key):
    [(value,)] = read(
        engine,
        "SELECT value FROM settings WHERE scope = :scope AND key = :key",
        scope=scope,
        key=key,
    )
    return value


def add_repo(engine, key, value, repo="repo:acme/app", actor="tester"):
    """Insert a repo row by SQL. The type is a placeholder. The table copies the real one from the org row."""
    run(
        engine,
        "INSERT INTO settings (scope, key, value, type, min_value, max_value) "
        "VALUES (:scope, :key, CAST(:value AS jsonb), 'str', NULL, NULL)",
        actor=actor,
        scope=repo,
        key=key,
        value=json.dumps(value),
    )
