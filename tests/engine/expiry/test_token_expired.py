from tests.support.scenario import EDIT_THEN_FINISH, make_context
from veil.engine import run
from veil.engine.errors.token_expired import TokenExpired


def expire(*_args, **_kwargs):
    raise TokenExpired("The token of the repository expired.")


def assert_all_untouched(tracker, keys):
    for key in keys:
        assert tracker.comments_on(key) == []
        assert tracker.labels_on(key) == []
        assert tracker.status_of(key) == "To Do"


def test_an_expired_token_stops_the_repo_and_leaves_every_ticket_for_the_next_run(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path, EDIT_THEN_FINISH, extra_tickets=[{"key": "GR-101"}]
    )
    repos.open_workspace = expire

    report = run(context)

    assert report.outcomes == {
        "GR-100": "left_for_next_run",
        "GR-101": "left_for_next_run",
    }
    assert report.stopped == "token_expired"
    assert model.models_used == []
    assert repos.pull_requests == []
    assert_all_untouched(tracker, ["GR-100", "GR-101"])


def test_a_token_that_expires_at_the_pr_leaves_the_fixed_ticket_for_the_next_run(
    tmp_path,
):
    context, tracker, repos, _ = make_context(tmp_path, EDIT_THEN_FINISH)
    repos.open_draft_pr = expire

    report = run(context)

    assert report.outcomes == {"GR-100": "left_for_next_run"}
    assert report.stopped == "token_expired"
    assert repos.pull_requests == []
    assert_all_untouched(tracker, ["GR-100"])


def test_a_run_without_an_expiry_reports_no_stop(tmp_path):
    context, _, _, _ = make_context(tmp_path, EDIT_THEN_FINISH)

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert report.stopped is None


def test_a_token_that_expires_while_the_engine_looks_for_existing_fixes_stops_the_repo(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path, EDIT_THEN_FINISH, extra_tickets=[{"key": "GR-101"}]
    )
    repos.find_existing_fix = expire

    report = run(context)

    assert report.outcomes == {
        "GR-100": "left_for_next_run",
        "GR-101": "left_for_next_run",
    }
    assert report.stopped == "token_expired"
    assert model.models_used == []
    assert_all_untouched(tracker, ["GR-100", "GR-101"])
