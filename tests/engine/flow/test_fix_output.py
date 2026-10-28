import pytest

from tests.fakes import finish
from tests.support.scenario import GOOD_EDIT, make_context
from veil.engine import run

LONG_EXPLANATION = "One. Two. Three. Four."


def test_the_commit_gets_the_message_of_the_model_and_the_pr_and_ticket_get_the_explanation(
    tmp_path,
):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [
            [GOOD_EDIT],
            [
                finish(
                    "The input is now an integer. Eval is gone.",
                    commit_message="Replace eval with int",
                )
            ],
        ],
    )

    run(context)

    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == ["Replace eval with int"]
    assert "The input is now an integer. Eval is gone." in pr.body
    [comment] = tracker.comments_on("GR-100")
    assert pr.url in comment
    assert "The input is now an integer." in comment


@pytest.mark.parametrize(
    ("bad_finish", "good_finish"),
    [
        (
            finish(LONG_EXPLANATION),
            finish("Short explanation.", commit_message="Replace eval"),
        ),
        (
            finish("One. two. three. four."),
            finish("Short explanation.", commit_message="Replace eval"),
        ),
        (
            finish("Short explanation.", commit_message="Line one\nLine two"),
            finish("Short explanation.", commit_message="Replace eval"),
        ),
    ],
    ids=[
        "explanation-over-3-sentences",
        "sentences-that-start-in-lower-case",
        "commit-message-with-two-lines",
    ],
)
def test_a_finish_that_breaks_the_format_is_refused_and_the_model_can_finish_again(
    tmp_path, bad_finish, good_finish
):
    context, _, repos, _ = make_context(
        tmp_path, [[GOOD_EDIT], [bad_finish], [good_finish]]
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == ["Replace eval"]
    assert "Short explanation." in pr.body
    assert LONG_EXPLANATION not in pr.body
    assert "Line two" not in pr.body


def test_an_abbreviation_does_not_count_as_the_end_of_a_sentence(tmp_path):
    explanation = "Fixed in e.g. a.py. Also b.py. Done."
    context, _, repos, _ = make_context(
        tmp_path, [[GOOD_EDIT], [finish(explanation, commit_message="Replace eval")]]
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert explanation in pr.body
