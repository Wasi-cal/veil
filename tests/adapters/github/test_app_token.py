import jwt
import pytest
from pydantic import SecretStr

from tests.adapters.github.support import (
    APP_ID,
    GOOD_PERMISSIONS,
    TOKEN,
    minted,
    source_for,
)
from tests.fakes.http_server import StubHttpServer
from veil.adapters.github.app_token import GitHubAppTokenSource
from veil.engine.errors.repo_provider_error import RepoProviderError

INSTALLATION_PATH = "/repos/acme/app/installation"
TOKEN_PATH = "/app/installations/77/access_tokens"


def serve(server, answer=None):
    server.routes[("GET", INSTALLATION_PATH)] = (200, {"id": 77})
    server.routes[("POST", TOKEN_PATH)] = answer or minted()


def test_it_mints_a_token_for_one_repo_with_two_permissions(key_pair):
    key, public = key_pair
    with StubHttpServer() as server:
        serve(server)

        token = source_for(server, key).mint("acme/app")

    assert token.get_secret_value() == TOKEN
    lookup, mint = server.seen
    claims = jwt.decode(
        lookup.authorization.removeprefix("Bearer "),
        public,
        algorithms=["RS256"],
        options={"verify_exp": False},
    )
    assert claims["iss"] == APP_ID
    assert 0 < claims["exp"] - claims["iat"] <= 600
    assert mint.authorization == lookup.authorization
    assert mint.body == {
        "repositories": ["app"],
        "permissions": {"contents": "write", "pull_requests": "write"},
    }


def test_it_stops_when_the_app_is_not_installed_on_the_repo(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        server.routes[("GET", INSTALLATION_PATH)] = (404, {"message": "Not Found"})

        with pytest.raises(RepoProviderError, match="installed"):
            source_for(server, key).mint("acme/app")

    assert [r.method for r in server.seen] == ["GET"]


def test_it_stops_when_github_refuses_the_key(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        server.routes[("GET", INSTALLATION_PATH)] = (401, {"message": "Bad"})

        with pytest.raises(RepoProviderError, match="401") as failure:
            source_for(server, key).mint("acme/app")

    assert key.get_secret_value() not in str(failure.value)


def test_it_stops_on_a_key_that_is_not_a_private_key_and_never_repeats_it():
    bad = SecretStr("not-a-pem-" + "x" * 30)
    with StubHttpServer() as server:
        serve(server)

        with pytest.raises(RepoProviderError, match="private key") as failure:
            GitHubAppTokenSource(APP_ID, bad, base_url=server.url).mint("acme/app")

    assert bad.get_secret_value() not in str(failure.value)
    assert server.seen == []


@pytest.mark.parametrize(
    "answer",
    [
        minted(repositories=("acme/app", "acme/other")),
        minted(repositories=("acme/other",)),
        minted(repositories=()),
        minted(selection="all"),
        minted(permissions={**GOOD_PERMISSIONS, "workflows": "write"}),
        minted(permissions={**GOOD_PERMISSIONS, "administration": "write"}),
        minted(permissions={"contents": "read", "pull_requests": "write"}),
        (201, {"token": "", "permissions": GOOD_PERMISSIONS}),
        (201, {"permissions": GOOD_PERMISSIONS}),
    ],
)
def test_it_refuses_a_token_that_fails_its_check(key_pair, answer):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(server, answer)

        with pytest.raises(RepoProviderError) as failure:
            source_for(server, key).mint("acme/app")

    assert TOKEN not in str(failure.value)


def test_it_refuses_a_bad_repo_name_before_any_call(key_pair):
    key, _ = key_pair
    with (
        StubHttpServer() as server,
        pytest.raises(RepoProviderError, match="repository name"),
    ):
        source_for(server, key).mint("acme/app/../other")

    assert server.seen == []


def test_it_accepts_a_reply_with_no_metadata_permission(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(
            server, minted(permissions={"contents": "write", "pull_requests": "write"})
        )

        assert source_for(server, key).mint("acme/app").get_secret_value() == TOKEN
