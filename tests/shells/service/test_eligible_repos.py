import pytest

from tests.adapters.github.support import minted, source_for
from tests.fakes.http_server import StubHttpServer
from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.adapters.redis.repo_list_cache import RepoListCache
from veil.engine import Settings
from veil.shells.service.eligible_repos import eligible_repos

INSTALLED = ["acme/app", "acme/web", "acme/api"]


def serve(server, repos=INSTALLED):
    server.routes[("GET", "/orgs/acme/installation")] = (200, {"id": 77})
    server.routes[("POST", "/app/installations/77/access_tokens")] = minted(
        permissions={"metadata": "read"}, repositories=()
    )
    server.routes[("GET", "/installation/repositories")] = (
        200,
        {"repositories": [{"full_name": name} for name in repos]},
    )


def eligible(key, settings=None, cache=None, repos=INSTALLED):
    with StubHttpServer() as server:
        serve(server, repos)
        found = eligible_repos(
            source_for(server, key), "acme", settings or Settings(), cache
        )
    return found, server


def test_with_no_allow_list_every_repo_of_the_installation_is_eligible(key_pair):
    key, _ = key_pair

    found, _ = eligible(key)

    assert found == INSTALLED


def test_the_allow_list_narrows_the_installation_and_never_widens_it(key_pair):
    key, _ = key_pair

    found, _ = eligible(key, Settings(repos_allow=("acme/web", "acme/not-installed")))

    assert found == ["acme/web"]


def test_the_deny_list_removes_a_repo(key_pair):
    key, _ = key_pair

    found, _ = eligible(key, Settings(repos_deny=("acme/web",)))

    assert found == ["acme/app", "acme/api"]


def test_a_repo_on_both_lists_is_denied(key_pair):
    key, _ = key_pair

    found, _ = eligible(
        key, Settings(repos_allow=("acme/app", "acme/web"), repos_deny=("acme/web",))
    )

    assert found == ["acme/app"]


@pytest.mark.parametrize("spelling", ["Acme/App", "ACME/APP"])
def test_a_name_in_the_lists_matches_whatever_the_case(key_pair, spelling):
    key, _ = key_pair

    allowed, _ = eligible(key, Settings(repos_allow=(spelling,)))
    denied, _ = eligible(key, Settings(repos_deny=(spelling,)))

    assert allowed == ["acme/app"]
    assert denied == ["acme/web", "acme/api"]


def test_the_list_comes_from_the_cache_after_the_first_call(key_pair, redis_url):
    key, _ = key_pair
    cache = RepoListCache(GuardedRedis.from_url(redis_url), ttl_seconds=600)

    _, first = eligible(key, cache=cache)
    found, second = eligible(key, cache=cache, repos=["acme/other"])

    assert found == INSTALLED
    assert any(r.path == "/installation/repositories" for r in first.seen)
    assert not any(r.method == "POST" for r in second.seen)
