import pytest

from tests.adapters.github.support import TOKEN
from tests.shells.github_action.support import JIRA_TOKEN, OPENAI_KEY, SpyRun


@pytest.mark.parametrize("value", [None, "", "   "])
def test_a_missing_or_blank_github_token_stops_the_run_and_names_the_variable(
    world, value
):
    if value is None:
        del world.environ["GITHUB_TOKEN"]
    else:
        world.environ["GITHUB_TOKEN"] = value

    code, spy = world.run_action()

    assert code == 1
    assert "GITHUB_TOKEN" in world.out.getvalue()
    assert spy.contexts == []
    assert world.jira.seen == []
    assert world.github.seen == []


def test_a_github_token_that_is_too_short_stops_the_run_without_showing_it(world):
    world.environ["GITHUB_TOKEN"] = "abc"

    code, spy = world.run_action()

    assert code == 1
    assert "GITHUB_TOKEN" in world.out.getvalue()
    assert "abc" not in world.out.getvalue().replace("GITHUB_TOKEN", "")
    assert spy.contexts == []


def test_the_engine_gets_the_github_token_of_the_workflow(world):
    code, spy = world.run_action()

    assert code == 0
    assert TOKEN in spy.contexts[0].credential_values


def test_every_credential_is_masked_before_the_engine_runs(world):
    code, spy = world.run_action()

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


def test_a_failure_never_repeats_the_github_token(world):
    from veil.engine.errors.repo_provider_error import RepoProviderError

    spy = SpyRun(world.out, error=RepoProviderError(f"failed with {TOKEN}"))

    code, _ = world.run_action(run=spy)

    assert code == 1
    unmasked = [
        line
        for line in world.out.getvalue().splitlines()
        if not line.startswith("::add-mask::")
    ]
    assert all(TOKEN not in line for line in unmasked)


def test_a_value_with_more_than_one_line_is_masked_line_by_line(world):
    world.run_action(GITHUB_TOKEN="first-line-of-secret\nsecond-line-of-secret")

    assert "::add-mask::first-line-of-secret\n" in world.out.getvalue()
    assert "::add-mask::second-line-of-secret\n" in world.out.getvalue()


def test_a_percent_sign_is_escaped_as_the_runner_needs(world):
    world.run_action(GITHUB_TOKEN="ab%cd-efghijkl")

    assert "::add-mask::ab%25cd-efghijkl\n" in world.out.getvalue()


def test_a_carriage_return_splits_a_value_into_lines_that_are_masked_apart(world):
    world.run_action(GITHUB_TOKEN="first-part-aaa\rsecond-part-bbb")

    assert "::add-mask::first-part-aaa\n" in world.out.getvalue()
    assert "::add-mask::second-part-bbb\n" in world.out.getvalue()
