import pytest

from tests.adapters.conftest import redis_url, shared_redis_url  # noqa: F401
from tests.fakes.http_server import StubHttpServer


@pytest.fixture
def stubs():
    with StubHttpServer() as jira, StubHttpServer() as github:
        yield jira, github
