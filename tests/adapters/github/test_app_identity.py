import pytest

from tests.adapters.github.support import APP_ID, GOOD_PERMISSIONS, source_for
from tests.fakes.http_server import StubHttpServer
from veil.engine.errors.repo_provider_error import RepoProviderError

APP_PATH = "/app"
BOT_PATH = "/users/gozu-veil%5Bbot%5D"


def serve(server, permissions=None, events=(), bot=(200, {"id": 9001})):
    server.routes[("GET", APP_PATH)] = (
        200,
        {
            "slug": "gozu-veil",
            "permissions": permissions or GOOD_PERMISSIONS,
            "events": list(events),
        },
    )
    server.routes[("GET", BOT_PATH)] = bot


def test_the_app_gives_the_bot_identity_with_a_stable_email(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(server)

        app = source_for(server, key).read_app()

    assert app.commit_author.name == "gozu-veil[bot]"
    assert app.commit_author.email == "9001+gozu-veil[bot]@users.noreply.github.com"


def test_the_app_call_carries_a_jwt_that_the_app_signed(key_pair):
    key, public = key_pair
    import jwt

    with StubHttpServer() as server:
        serve(server)

        source_for(server, key).read_app()

    call = server.seen[0]
    claims = jwt.decode(
        call.authorization.removeprefix("Bearer "),
        public,
        algorithms=["RS256"],
        options={"verify_exp": False},
    )
    assert claims["iss"] == APP_ID


@pytest.mark.parametrize(
    "permissions",
    [
        {**GOOD_PERMISSIONS, "workflows": "write"},
        {**GOOD_PERMISSIONS, "administration": "read"},
        {**GOOD_PERMISSIONS, "organization_administration": "read"},
        {"contents": "read", "pull_requests": "write", "metadata": "read"},
        {"contents": "write", "metadata": "read"},
    ],
)
def test_it_refuses_an_app_with_other_permissions_than_the_three(key_pair, permissions):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(server, permissions=permissions)

        with pytest.raises(RepoProviderError, match="permissions"):
            source_for(server, key).read_app()


def test_it_refuses_an_app_that_listens_to_events(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(server, events=["push"])

        with pytest.raises(RepoProviderError, match="events"):
            source_for(server, key).read_app()


def test_it_stops_when_github_does_not_know_the_bot_user(key_pair):
    key, _ = key_pair
    with StubHttpServer() as server:
        serve(server, bot=(404, {"message": "Not Found"}))

        with pytest.raises(RepoProviderError):
            source_for(server, key).read_app()
