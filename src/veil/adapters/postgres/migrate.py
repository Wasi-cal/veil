import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text

from veil.adapters.postgres.constants.database import (
    BASE_REVISION,
    HEAD_REVISION,
    MIGRATION_LOCK_KEY,
)
from veil.adapters.postgres.constants.scopes import DATABASE_URL_VARIABLE


def _config(connection: Connection) -> Config:
    """An Alembic setup that works on the given connection. The URL of the database is not in it."""
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.attributes["connection"] = connection
    return config


def _take_turn(connection: Connection) -> None:
    """Wait until no other deployment migrates this database. The lock ends with the transaction."""
    connection.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": MIGRATION_LOCK_KEY}
    )


def apply_migrations(engine: Engine) -> None:
    """Apply every migration that is not applied yet, in order. A repeat changes nothing.

    Deployment calls this, or runs `alembic upgrade head`. All the changes run in one transaction.
    """
    with engine.begin() as connection:
        _take_turn(connection)
        command.upgrade(_config(connection), HEAD_REVISION)


def revert_migrations(engine: Engine) -> None:
    """Undo every migration. This is for tests and for a database that nobody uses."""
    with engine.begin() as connection:
        _take_turn(connection)
        command.downgrade(_config(connection), BASE_REVISION)


def main() -> None:
    """Apply the migrations to the database that the variable VEIL_DATABASE_URL names.

    Deployment runs this: `python -m veil.adapters.postgres.migrate`.
    """
    url = os.environ.get(DATABASE_URL_VARIABLE)
    if not url:
        raise SystemExit(f"Set {DATABASE_URL_VARIABLE} to the URL of the database.")
    engine = create_engine(url)
    try:
        apply_migrations(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
