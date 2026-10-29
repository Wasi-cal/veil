import pytest

from tests.adapters.github.support import TOKEN
from tests.shells.github_action.support import (
    JIRA_TOKEN,
    OPENAI_KEY,
    FakeTokenSource,
    SpyRun,
)
from veil.engine.errors.repo_provider_error import RepoProviderError


def unmasked(text):
    """The log without the mask commands. A mask command holds the value on purpose."""
    return "\n".join(l for l in text.splitlines() if not l.startswith("::add-mask::"))


def test_a_failed_mint_stops_the_run_with_a_clear_failure_and_touches_no_ticket(world):
    source = FakeTokenSource(
        error=RepoProviderError("The GitHub App is not installed.")
    )

    code, spy, _ = world.run_action(token_source=source)

    assert code == 1
    assert "::error::" in world.out.getvalue()
    assert "The GitHub App is not installed." in world.out.getvalue()
    assert spy.contexts == []
    assert world.jira.seen == []
    assert world.github.seen == []


def test_the_failure_never_repeats_a_credential(world):
    source = FakeTokenSource(error=RepoProviderError(f"bad {JIRA_TOKEN} {OPENAI_KEY}"))

    world.run_action(token_source=source)

    for value in (JIRA_TOKEN, OPENAI_KEY):
        assert value not in unmasked(world.out.getvalue())


@pytest.mark.parametrize("missing", ["GOZU_APP_ID", "GOZU_APP_PRIVATE_KEY"])
def test_a_missing_app_variable_stops_the_run_and_names_the_variable(world, missing):
    from veil.shells.github_action.run_action import run_action

    del world.environ[missing]

    code = run_action(world.environ, urls=world.urls, out=world.out)

    assert code == 1
    assert missing in world.out.getvalue()
    assert world.jira.seen == []


def test_the_action_has_no_other_token_to_fall_back_on(world):
    from veil.shells.github_action.run_action import run_action

    world.environ["GITHUB_TOKEN"] = TOKEN
    del world.environ["GOZU_APP_PRIVATE_KEY"]

    code = run_action(world.environ, urls=world.urls, out=world.out)

    assert code == 1
    assert world.github.seen == []
    assert TOKEN not in world.out.getvalue()


def test_every_credential_is_masked_before_the_engine_runs(world):
    code, spy, _ = world.run_action()

    assert code == 0
    before = spy.printed_before[0]
    for value in (TOKEN, JIRA_TOKEN, OPENAI_KEY):
        assert f"::add-mask::{value}" in before


def test_the_token_is_masked_before_anything_else_can_print_it(world):
    world.run_action()

    first_use = world.out.getvalue().index(TOKEN)

    assert world.out.getvalue().index(f"::add-mask::{TOKEN}") == first_use - len(
        "::add-mask::"
    )


def test_a_value_with_more_than_one_line_is_masked_line_by_line(world):
    value = "first-line-of-secret\nsecond-line-of-secret"

    world.run_action(token_source=FakeTokenSource(token=value))

    assert "::add-mask::first-line-of-secret\n" in world.out.getvalue()
    assert "::add-mask::second-line-of-secret\n" in world.out.getvalue()


def test_a_percent_sign_is_escaped_as_the_runner_needs(world):
    world.run_action(token_source=FakeTokenSource(token="ab%cd-efghijkl"))

    assert "::add-mask::ab%25cd-efghijkl\n" in world.out.getvalue()


def test_a_carriage_return_splits_a_value_into_lines_that_are_masked_apart(world):
    world.run_action(
        token_source=FakeTokenSource(token="first-part-aaa\rsecond-part-bbb")
    )

    assert "::add-mask::first-part-aaa\n" in world.out.getvalue()
    assert "::add-mask::second-part-bbb\n" in world.out.getvalue()


def test_the_app_key_is_masked_too(world):
    from tests.shells.github_action.support import APP_KEY
    from veil.shells.github_action.run_action import run_action

    spy = SpyRun(world.out)
    run_action(world.environ, urls=world.urls, run=spy, out=world.out)

    body_line = APP_KEY.splitlines()[1]
    assert f"::add-mask::{body_line}\n" in world.out.getvalue()


def test_a_github_token_variable_is_never_used_when_the_app_is_set_up(world):
    other = "ghs_" + "Z9" * 18
    world.environ["GITHUB_TOKEN"] = other

    code, spy, _ = world.run_action()

    assert code == 0
    assert other not in spy.contexts[0].credential_values
    assert other not in world.out.getvalue()
