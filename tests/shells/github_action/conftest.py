import pytest

from tests.fakes.http_server import StubHttpServer
from tests.shells.github_action.support import World


@pytest.fixture
def world(tmp_path):
    with StubHttpServer() as jira, StubHttpServer() as github:
        yield World(tmp_path, jira, github)
