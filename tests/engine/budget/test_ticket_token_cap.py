import pytest
from pydantic import ValidationError

from tests.engine.grouping.test_one_pr_per_ticket import BUGGY, fix_of
from tests.fakes import edit_file, read_file
from tests.support.scenario import EDIT_THEN_FINISH, FIXED, make_context, toggle_edits
from veil.engine import ModelReply, Settings, run


def test_a_ticket_that_passes_its_cap_is_a_failed_fix_and_the_run_goes_on(tmp_path):
    """Ticket one: the cheap attempt uses 600 tokens. The strong attempt reaches 900. The cap is 800."""
    context, tracker, repos, model = make_context(
        tmp_path,
        {
            "small": [*toggle_edits(2), *EDIT_THEN_FINISH],
            "big": toggle_edits(2),
        },
        tokens_per_call=300,
        settings=Settings(
            step_cap=2, cheap_model="small", strong_model="big", ticket_token_cap=800
        ),
        extra_tickets=[{"key": "GR-101", "line": 3}],
    )

    report = run(context)

    assert model.models_used == ["small", "small", "big", "small", "small"]
    assert report.outcomes == {"GR-100": "failed", "GR-101": "fixed"}
    assert report.tokens_used == 1500
    assert tracker.labels_on("GR-100") == ["veil-failed-fix"]
    assert tracker.status_of("GR-100") == "To Do"
    [comment] = tracker.comments_on("GR-100")
    assert "token cap of 800" in comment
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED
    assert report.reasons["GR-100"].startswith("The ticket used its token cap of 800")


def test_the_report_splits_the_tokens_of_each_ticket_by_model(tmp_path):
    context, _, _, _ = make_context(
        tmp_path,
        {
            "small": [*toggle_edits(2), *EDIT_THEN_FINISH],
            "big": toggle_edits(2),
        },
        tokens_per_call=300,
        settings=Settings(
            step_cap=2, cheap_model="small", strong_model="big", ticket_token_cap=800
        ),
        extra_tickets=[{"key": "GR-101", "line": 3}],
    )

    report = run(context)

    failed, fixed = report.usage["GR-100"], report.usage["GR-101"]
    assert failed.escalated
    assert (failed.input, failed.output, failed.total) == (600, 300, 900)
    assert {m: t.total for m, t in failed.by_model.items()} == {
        "small": 600,
        "big": 300,
    }
    assert not fixed.escalated
    assert list(fixed.by_model) == ["small"]
    assert (fixed.input, fixed.output) == (400, 200)


def test_the_cap_is_for_each_ticket_and_not_for_the_run(tmp_path):
    """Each Fix needs 600 tokens. The cap is 800. The run uses 1800 tokens."""
    context, _, repos, _ = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a"), *fix_of("b.py", "Fix b"), *fix_of("c.py", "Fix c")],
        tokens_per_call=300,
        files={"a.py": BUGGY, "b.py": BUGGY, "c.py": BUGGY},
        file="a.py",
        settings=Settings(ticket_token_cap=800),
        extra_tickets=[
            {"key": "GR-101", "file": "b.py"},
            {"key": "GR-102", "file": "c.py"},
        ],
    )

    report = run(context)

    assert set(report.outcomes.values()) == {"fixed"}
    assert report.tokens_used == 1800
    assert len(repos.pull_requests) == 3


def test_a_fix_that_finishes_is_published_even_if_its_last_call_passes_the_cap(
    tmp_path,
):
    context, _, repos, _ = make_context(
        tmp_path,
        EDIT_THEN_FINISH,
        tokens_per_call=300,
        settings=Settings(ticket_token_cap=500),
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert report.tokens_used == 600
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED


def test_a_failed_ticket_leaves_no_edit_for_the_next_ticket_of_the_same_file(tmp_path):
    """Ticket one edits the file, reads it, and passes its cap of 400 tokens. Ticket two starts from clean files."""
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", "eval(input())", "int(input())")],
            [read_file("app.py")],
            *EDIT_THEN_FINISH,
        ],
        tokens_per_call=300,
        settings=Settings(ticket_token_cap=400),
        extra_tickets=[{"key": "GR-101", "line": 3}],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "failed", "GR-101": "fixed"}
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED
    assert len(repos.commit_subjects_on(pr)) == 1


def test_the_cap_must_be_a_positive_number():
    with pytest.raises(ValidationError):
        Settings(ticket_token_cap=0)


def test_the_old_run_ceiling_is_gone():
    with pytest.raises(ValidationError):
        Settings(token_ceiling=800)


def test_a_model_reply_must_report_its_tokens():
    """A client that forgets the usage would turn the cap off without a sign."""
    with pytest.raises(ValidationError):
        ModelReply(tool_calls=[])
