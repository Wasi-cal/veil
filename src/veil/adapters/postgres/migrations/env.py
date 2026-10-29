"""The Alembic environment. A caller gives a connection, or the program reads VEIL_DATABASE_URL."""

import os

from alembic import context
from sqlalchemy import Connection, create_engine

from veil.adapters.postgres.constants.scopes import DATABASE_URL_VARIABLE
from veil.adapters.postgres.orm.base import Base

config = context.config


def run_migrations() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _migrate(connection)
        return
    engine = create_engine(os.environ[DATABASE_URL_VARIABLE])
    try:
        with engine.begin() as own_connection:
            _migrate(own_connection)
    finally:
        engine.dispose()


def _migrate(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


run_migrations()
