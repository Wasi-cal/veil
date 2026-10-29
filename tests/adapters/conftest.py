import os
import uuid
from collections.abc import Iterator

import pytest
import redis
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from tests.support.postgres_server import find_program, running_server
from tests.support.redis_server import RunningRedis, find_redis_server, running_redis

POSTGRES_URL_VARIABLE = "VEIL_TEST_DATABASE_URL"
REDIS_URL_VARIABLE = "VEIL_TEST_REDIS_URL"
# CI sets this. A missing server then fails the run, and the tests of a stopped server do not skip.
REQUIRE_VARIABLE = "VEIL_REQUIRE_TEST_SERVICES"


def _missing(reason: str) -> None:
    """Skip the test because a server is missing. When CI requires the servers, fail instead."""
    if os.environ.get(REQUIRE_VARIABLE):
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope="session")
def admin_url() -> Iterator[str]:
    """The admin URL of a server for the tests. A set POSTGRES_URL_VARIABLE wins. Else a throwaway server starts."""
    given = os.environ.get(POSTGRES_URL_VARIABLE)
    if given:
        yield given
        return
    if not (find_program("initdb") and find_program("pg_ctl")):
        _missing(
            f"No PostgreSQL programs on this machine. Set {POSTGRES_URL_VARIABLE} to use a server."
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


@pytest.fixture(scope="session")
def shared_redis_url() -> Iterator[str]:
    """The URL of a Redis for the tests. A set REDIS_URL_VARIABLE wins. Else a throwaway server starts."""
    given = os.environ.get(REDIS_URL_VARIABLE)
    if given:
        yield given
        return
    if find_redis_server() is None:
        _missing(
            f"No redis-server on this machine. Set {REDIS_URL_VARIABLE} to use a server."
        )
    with running_redis() as server:
        yield server.url


@pytest.fixture
def redis_url(shared_redis_url: str) -> str:
    """A Redis with no keys."""
    redis.Redis.from_url(shared_redis_url).flushall()
    return shared_redis_url


@pytest.fixture
def stoppable_redis() -> Iterator[RunningRedis]:
    """A Redis of its own that a test can stop and start again."""
    if find_redis_server() is None:
        _missing("No redis-server on this machine.")
    with running_redis() as server:
        yield server
