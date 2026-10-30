import pytest

from tests.fakes.http_server import StubHttpServer


@pytest.fixture
def stubs():
    with StubHttpServer() as jira, StubHttpServer() as github:
        yield jira, github
