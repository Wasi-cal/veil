import pytest
from pydantic import ValidationError

from tests.support.scenario import EDIT_THEN_FINISH, FIXED, make_context, toggle_edits
from veil.engine import ModelReply, Settings, run


def test_ceiling_counts_all_attempts_and_leaves_the_rest_for_the_next_run(tmp_path):
    """The cheap attempt uses 600 tokens. The strong attempt reaches 900. The ceiling is 800."""
    context, tracker, repos, model = make_context(
        tmp_path,
        {"small": toggle_edits(2), "big": toggle_edits(2)},
        tokens_per_call=300,
        settings=Settings(
            step_cap=2, cheap_model="small", strong_model="big", token_ceiling=800
        ),
        extra_tickets=[{"key": "GR-101"}],
    )

    report = run(context)

    assert model.models_used == ["small", "small", "big"]
    assert report.tokens_used == 900
    assert report.outcomes == {
        "GR-100": "left_for_next_run",
        "GR-101": "left_for_next_run",
    }
    assert repos.pull_requests == []
    for key in ("GR-100", "GR-101"):
        assert tracker.comments_on(key) == []
        assert tracker.labels_on(key) == []
        assert tracker.status_of(key) == "To Do"


def test_fix_that_finishes_is_published_even_if_its_last_call_passes_the_ceiling(
    tmp_path,
):
    context, _, repos, _ = make_context(
        tmp_path,
        EDIT_THEN_FINISH,
        tokens_per_call=300,
        settings=Settings(token_ceiling=500),
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert report.tokens_used == 600
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED


def test_a_model_reply_must_report_its_tokens():
    """A client that forgets the usage would turn the ceiling off without a sign."""
    with pytest.raises(ValidationError):
        ModelReply(tool_calls=[])
