import pytest

from tests.fakes.http_server import StubHttpServer
from veil.adapters.jira.gateway import resolve_api_base
from veil.engine.errors.tracker_error import TrackerError


def test_the_gateway_url_comes_from_the_cloud_id_of_the_site():
    with StubHttpServer() as site:
        site.routes[("GET", "/_edge/tenant_info")] = (200, {"cloudId": "abc-123"})

        base = resolve_api_base(site.url)

    assert base == "https://api.atlassian.com/ex/jira/abc-123"


def test_a_site_that_gives_no_cloud_id_is_an_error():
    with StubHttpServer() as site:
        site.routes[("GET", "/_edge/tenant_info")] = (404, {})

        with pytest.raises(TrackerError):
            resolve_api_base(site.url)
