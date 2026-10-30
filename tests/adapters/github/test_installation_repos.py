import pytest

from tests.adapters.github.support import TOKEN, minted, source_for
from tests.fakes.http_server import StubHttpServer
from veil.engine.errors.repo_provider_error import RepoProviderError

ORG_PATH = "/orgs/acme/installation"
USER_PATH = "/users/acme/installation"
TOKEN_PATH = "/app/installations/77/access_tokens"
LIST_PATH = "/installation/repositories"
METADATA_ONLY = {"metadata": "read"}


def listing(*names):
    return (200, {"repositories": [{"full_name": name} for name in names]})


def serve(server, pages=None, token=None):
    server.routes[("GET", ORG_PATH)] = (200, {"id": 77})
    server.routes[("POST", TOKEN_PATH)] = token or minted(
        permissions=METADATA_ONLY, repositories=()
    )
    server.routes[("GET", LIST_PATH)] = pages or listing("acme/app", "acme/web")


def test_it_lists_the_repos_of_the_installation_of_an_org(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(server)
        source = source_for(server, key)

        repos = source.list_repos(source.installation_id("acme"))

    assert repos == ["acme/app", "acme/web"]


def test_the_token_for_the_list_reads_metadata_only_and_goes_only_to_the_list_call(
    key_pair,
):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(server)
        source = source_for(server, key)

        source.list_repos(source.installation_id("acme"))

    mint = next(r for r in server.seen if r.method == "POST")
    assert mint.body == {"permissions": METADATA_ONLY}
    [listed] = [r for r in server.seen if r.path == LIST_PATH]
    assert listed.authorization == f"Bearer {TOKEN}"
    assert [r.path for r in server.seen if TOKEN in (r.authorization or "")] == [
        LIST_PATH
    ]


def test_it_reads_every_page_of_the_list(key_pair):
    key, _ = key_pair
    first = [f"acme/repo-{n}" for n in range(100)]
    with StubHttpServer() as server:
        serve(server, pages=[listing(*first), listing("acme/last")])
        source = source_for(server, key)

        repos = source.list_repos(source.installation_id("acme"))

    assert repos == [*first, "acme/last"]
    pages = [r.query["page"] for r in server.seen if r.path == LIST_PATH]
    assert pages == [["1"], ["2"]]


def test_a_user_account_has_an_installation_too(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        server.routes[("GET", ORG_PATH)] = (404, {"message": "Not Found"})
        server.routes[("GET", USER_PATH)] = (200, {"id": 77})

        assert source_for(server, key).installation_id("acme") == 77


def test_it_stops_when_the_app_is_not_installed_on_the_account(key_pair):
    key, _ = key_pair
    with (
        StubHttpServer() as server,
        pytest.raises(RepoProviderError, match="not installed"),
    ):
        source_for(server, key).installation_id("acme")


def test_it_refuses_a_token_for_the_list_that_holds_more_than_metadata(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(
            server,
            token=minted(
                permissions={"metadata": "read", "contents": "write"}, repositories=()
            ),
        )
        source = source_for(server, key)

        with pytest.raises(RepoProviderError, match="permissions") as failure:
            source.list_repos(source.installation_id("acme"))

    assert TOKEN not in str(failure.value)
    assert [r.path for r in server.seen if r.path == LIST_PATH] == []


@pytest.mark.parametrize("owner", ["acme/../x", "-acme", "acme app", "", "a" * 40])
def test_it_refuses_an_account_name_that_is_not_a_login_before_any_call(
    key_pair, owner
):
    key, _ = key_pair
    with StubHttpServer() as server, pytest.raises(RepoProviderError, match="account"):
        source_for(server, key).installation_id(owner)

    assert server.seen == []


def test_it_stops_on_a_list_that_never_ends(key_pair):
    key, _ = key_pair
    full_page = listing(*[f"acme/repo-{n}" for n in range(100)])
    with StubHttpServer() as server:
        serve(server, pages=[full_page])
        source = source_for(server, key)

        with pytest.raises(RepoProviderError, match="pages"):
            source.list_repos(source.installation_id("acme"))

    assert len([r for r in server.seen if r.path == LIST_PATH]) == 50
