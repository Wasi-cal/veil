import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from tests.support.postgres_server import find_program, running_server

URL_VARIABLE = "VEIL_TEST_DATABASE_URL"


@pytest.fixture(scope="session")
def admin_url() -> Iterator[str]:
    """The admin URL of a server for the tests. A set URL_VARIABLE wins. Else a throwaway server starts."""
    given = os.environ.get(URL_VARIABLE)
    if given:
        yield given
        return
    if not (find_program("initdb") and find_program("pg_ctl")):
        pytest.skip(
            f"No PostgreSQL programs on this machine. Set {URL_VARIABLE} to use a server."
        )
    with running_server() as url:
        yield url


def _create_database(admin_url: str, template: str | None = None) -> str:
    name = f"veil_{uuid.uuid4().hex[:12]}"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        suffix = f' TEMPLATE "{template}"' if template else ""
        connection.execute(text(f'CREATE DATABASE "{name}"{suffix}'))
    admin.dispose()
    return str(
        make_url(admin_url).set(database=name).render_as_string(hide_password=False)
    )


def _drop_database(admin_url: str, url: str) -> None:
    name = make_url(url).database
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture
def empty_engine(admin_url: str) -> Iterator[Engine]:
    """An engine for a new empty database. Nothing is migrated."""
    url = _create_database(admin_url)
    engine = create_engine(url)
    yield engine
    engine.dispose()
    _drop_database(admin_url, url)


@pytest.fixture(scope="session")
def migrated_template(admin_url: str) -> Iterator[str]:
    """The name of a database with every migration applied. Each test copies it."""
    from veil.adapters.postgres.migrate import apply_migrations

    url = _create_database(admin_url)
    engine = create_engine(url)
    apply_migrations(engine)
    engine.dispose()
    yield make_url(url).database
    _drop_database(admin_url, url)


@pytest.fixture
def engine(admin_url: str, migrated_template: str) -> Iterator[Engine]:
    """An engine for a copy of the migrated database. A test may change it."""
    url = _create_database(admin_url, template=migrated_template)
    engine = create_engine(url)
    yield engine
    engine.dispose()
    _drop_database(admin_url, url)
