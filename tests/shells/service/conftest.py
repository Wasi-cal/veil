import pytest

from tests.adapters.conftest import (  # noqa: F401
    admin_url,
    engine,
    migrated_template,
)
from tests.fakes.http_server import StubHttpServer


@pytest.fixture
def stubs():
    with StubHttpServer() as jira, StubHttpServer() as github:
        yield jira, github


@pytest.fixture(scope="session")
def temporal_host():
    """The host of a Temporal dev server. A set VEIL_TEST_TEMPORAL_HOST wins. Else a throwaway server starts."""
    import os

    from tests.adapters.conftest import REQUIRE_VARIABLE
    from tests.support.temporal_server import find_temporal, running_temporal

    given = os.environ.get("VEIL_TEST_TEMPORAL_HOST")
    if given:
        yield given
        return
    if find_temporal() is None:
        if os.environ.get(REQUIRE_VARIABLE):
            pytest.fail("No temporal program on this machine.")
        pytest.skip("No temporal program on this machine. Set VEIL_TEST_TEMPORAL_HOST.")
    with running_temporal() as host:
        yield host
