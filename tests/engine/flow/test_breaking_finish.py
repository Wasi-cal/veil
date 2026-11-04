import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import (
    CHEAP,
    CREDENTIAL,
    EDIT_THEN_FINISH,
    GOOD_EDIT,
    STRONG,
    assert_nowhere,
    make_context,
)
from veil.engine import run

REASON = "The function parse no longer accepts a string."
FOUR_SENTENCES = "One. Two. Three. Four."
LONG_SENTENCE = " ".join(["word"] * 26) + "."
RETRY = "Short explanation."


def test_a_finish_that_says_breaking_with_a_reason_ends_the_attempt(tmp_path):
    context, _, repos, model = make_context(
        tmp_path,
        [[GOOD_EDIT], [finish(RETRY, breaking=True, breaking_reason=REASON)]],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert len(model.received) == 2
    assert len(repos.pull_requests) == 1


def test_a_finish_that_says_breaking_with_no_reason_is_refused_and_the_model_can_finish_again(
    tmp_path,
):
    context, _, repos, model = make_context(
        tmp_path,
        [
            [GOOD_EDIT],
            [finish(RETRY, breaking=True)],
            [finish(RETRY, breaking=True, breaking_reason=REASON)],
        ],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    refusal = model.received[2][-1]["content"]
    assert refusal.startswith("Error:")
    assert "breaking_reason" in refusal
    assert len(repos.pull_requests) == 1


def test_a_finish_with_no_breaking_answer_is_refused(tmp_path):
    no_answer = finish(RETRY)
    del no_answer.arguments["breaking"]
    context, _, _, model = make_context(
        tmp_path, [[GOOD_EDIT], [no_answer], [finish(RETRY)]]
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert model.received[2][-1]["content"].startswith("Error:")


@pytest.mark.parametrize(
    "reason",
    [
        FOUR_SENTENCES,
        LONG_SENTENCE,
        "Avoid eval on user input.",
        "  ",
    ],
    ids=["over-3-sentences", "sentence-over-25-words", "copy-of-the-ticket", "blank"],
)
def test_a_bad_breaking_reason_is_refused_and_the_model_can_finish_again(
    tmp_path, reason
):
    context, _, _, model = make_context(
        tmp_path,
        [
            [GOOD_EDIT],
            [finish(RETRY, breaking=True, breaking_reason=reason)],
            [finish(RETRY, breaking=True, breaking_reason=REASON)],
        ],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert model.received[2][-1]["content"].startswith("Error:")


def test_a_reason_is_not_checked_when_the_fix_is_not_breaking(tmp_path):
    context, _, _, model = make_context(
        tmp_path,
        [[GOOD_EDIT], [finish(RETRY, breaking=False, breaking_reason=FOUR_SENTENCES)]],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert len(model.received) == 2


@pytest.mark.parametrize("secret", [CREDENTIAL], ids=["credential-of-this-run"])
def test_a_secret_in_the_breaking_reason_fails_the_attempt(tmp_path, secret):
    bad_finish = finish(
        RETRY, breaking=True, breaking_reason=f"The value {secret} is gone."
    )
    context, tracker, repos, model = make_context(
        tmp_path,
        {
            CHEAP: [
                [edit_file("app.py", "eval(input())", "int(input())")],
                [bad_finish],
            ],
            STRONG: EDIT_THEN_FINISH,
        },
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert_nowhere(secret, tracker, repos, report, model=model)
