from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.adapters.github.support import TOKEN
from tests.shells.github_action.support import SpyRun
from veil.shells.github_action.run_action import run_action


def test_without_a_given_token_source_the_action_mints_from_the_app_variables(world):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    world.environ["GOZU_APP_PRIVATE_KEY"] = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    world.github.routes[("GET", "/repos/acme/app/installation")] = (200, {"id": 5})
    world.github.routes[("POST", "/app/installations/5/access_tokens")] = (
        201,
        {
            "token": TOKEN,
            "permissions": {"contents": "write", "pull_requests": "write"},
            "repository_selection": "selected",
            "repositories": [{"full_name": "acme/app"}],
        },
    )
    spy = SpyRun(world.out)

    code = run_action(world.environ, urls=world.urls, run=spy, out=world.out)

    assert code == 0
    assert TOKEN in spy.contexts[0].credential_values
    assert f"::add-mask::{TOKEN}" in spy.printed_before[0]


def test_an_app_that_is_not_installed_stops_the_run_with_a_clear_failure(world):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    world.environ["GOZU_APP_PRIVATE_KEY"] = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    spy = SpyRun(world.out)

    code = run_action(world.environ, urls=world.urls, run=spy, out=world.out)

    assert code == 1
    assert "not installed on acme/app" in world.out.getvalue()
    assert spy.contexts == []
    assert world.jira.seen == []
