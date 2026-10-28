from tests.fakes import edit_file, finish
from tests.support.scenario import make_context
from veil.engine import FixQuery, Settings, run

BUGGY = "value = eval(input())\n"
FIXED_LINE = "value = int(input())\n"


def fix_of(path, commit_message):
    """The script of one ticket: edit one file and finish."""
    return [
        [edit_file(path, "eval(input())", "int(input())")],
        [finish(f"Changed {path}.", commit_message=commit_message)],
    ]


def test_low_and_medium_fixes_of_one_source_pr_go_into_one_shared_pr(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a"), *fix_of("b.py", "Fix b")],
        files={"a.py": BUGGY, "b.py": BUGGY},
        file="a.py",
        severity="Medium",
        extra_tickets=[{"key": "GR-101", "file": "b.py", "severity": "Low"}],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed", "GR-101": "fixed"}
    [pr] = repos.pull_requests
    assert report.pull_requests == [pr.url]
    assert pr.draft is True
    assert pr.base == "feature"
    assert repos.commit_subjects_on(pr) == ["Fix a", "Fix b"]
    assert repos.file_on(pr, "a.py") == FIXED_LINE
    assert repos.file_on(pr, "b.py") == FIXED_LINE
    assert "Changed a.py." in pr.body
    assert "Changed b.py." in pr.body
    assert repos.workspaces_opened == 1
    for key, label in (("GR-100", "issue-gr-100"), ("GR-101", "issue-gr-101")):
        assert pr.url in tracker.comments_on(key)[0]
        assert tracker.status_of(key) == "In Review"
        query = FixQuery(
            repo="acme/app",
            issue_label=label,
            source_branch="feature",
            branch_prefix="gozu/fix-",
        )
        assert repos.find_existing_fix(query) == "open_pr"


def toggles(path, count):
    """`count` valid edits of one file that never finish."""
    pairs = [("eval(input())", "int(input())"), ("int(input())", "eval(input())")]
    return [[edit_file(path, *pairs[n % 2])] for n in range(count)]


def test_a_failed_fix_stays_out_of_the_shared_pr_and_leaves_no_edit_in_it(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path,
        {
            "cheap-model": [
                *fix_of("a.py", "Fix a"),
                *toggles("b.py", 3),
                *fix_of("c.py", "Fix c"),
            ],
            "strong-model": toggles("b.py", 3),
        },
        files={"a.py": BUGGY, "b.py": BUGGY, "c.py": BUGGY},
        file="a.py",
        settings=Settings(step_cap=3),
        extra_tickets=[
            {"key": "GR-101", "file": "b.py"},
            {"key": "GR-102", "file": "c.py"},
        ],
    )

    report = run(context)

    assert report.outcomes == {
        "GR-100": "fixed",
        "GR-101": "failed",
        "GR-102": "fixed",
    }
    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == ["Fix a", "Fix c"]
    assert repos.changed_paths_on(pr) == {"a.py", "c.py"}
    assert repos.file_on(pr, "b.py") == BUGGY
    assert tracker.labels_on("GR-101") == ["veil-failed-fix"]
    assert tracker.status_of("GR-101") == "To Do"
    assert tracker.labels_on("GR-100") == []


def test_a_shared_pr_holds_at_most_the_cap_and_the_next_run_takes_the_rest(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a"), *fix_of("b.py", "Fix b"), *fix_of("c.py", "Fix c")],
        files={"a.py": BUGGY, "b.py": BUGGY, "c.py": BUGGY},
        file="a.py",
        settings=Settings(shared_pr_max=2),
        extra_tickets=[
            {"key": "GR-101", "file": "b.py"},
            {"key": "GR-102", "file": "c.py"},
        ],
    )

    first = run(context)

    assert first.outcomes == {
        "GR-100": "fixed",
        "GR-101": "fixed",
        "GR-102": "left_for_next_run",
    }
    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == ["Fix a", "Fix b"]
    assert tracker.comments_on("GR-102") == []
    assert tracker.status_of("GR-102") == "To Do"

    second = run(context)

    assert second.outcomes == {
        "GR-100": "skipped",
        "GR-101": "skipped",
        "GR-102": "fixed",
    }
    assert len(repos.pull_requests) == 2
    assert repos.commit_subjects_on(repos.pull_requests[1]) == ["Fix c"]


def test_tickets_of_different_source_prs_get_separate_shared_prs(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a"), *fix_of("b.py", "Fix b")],
        files={"a.py": BUGGY, "b.py": BUGGY},
        file="a.py",
        branch="feature-one",
        extra_tickets=[{"key": "GR-101", "file": "b.py", "branch": "feature-two"}],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed", "GR-101": "fixed"}
    first, second = repos.pull_requests
    assert {first.base, second.base} == {"feature-one", "feature-two"}
    assert first.head != second.head
    assert repos.commit_subjects_on(first) in (["Fix a"], ["Fix b"])


def test_at_the_token_ceiling_the_fixes_that_passed_are_published_and_the_rest_wait(
    tmp_path,
):
    """Ticket one needs 600 tokens. Ticket two starts at 600 and reaches 900. The ceiling is 800."""
    context, tracker, repos, _ = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a"), *fix_of("b.py", "Fix b"), *fix_of("c.py", "Fix c")],
        tokens_per_call=300,
        files={"a.py": BUGGY, "b.py": BUGGY, "c.py": BUGGY},
        file="a.py",
        settings=Settings(token_ceiling=800),
        extra_tickets=[
            {"key": "GR-101", "file": "b.py"},
            {"key": "GR-102", "file": "c.py"},
        ],
    )

    report = run(context)

    assert report.outcomes == {
        "GR-100": "fixed",
        "GR-101": "left_for_next_run",
        "GR-102": "left_for_next_run",
    }
    assert report.tokens_used == 900
    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == ["Fix a"]
    assert repos.changed_paths_on(pr) == {"a.py"}
    for key in ("GR-101", "GR-102"):
        assert tracker.comments_on(key) == []
        assert tracker.labels_on(key) == []


def test_a_second_run_after_a_shared_pr_creates_nothing(tmp_path):
    context, tracker, repos, model = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a"), *fix_of("b.py", "Fix b")],
        files={"a.py": BUGGY, "b.py": BUGGY},
        file="a.py",
        extra_tickets=[{"key": "GR-101", "file": "b.py"}],
    )
    run(context)
    calls_after_first_run = len(model.models_used)

    report = run(context)

    assert report.skipped == {"open_pr": ["GR-100", "GR-101"]}
    assert len(repos.pull_requests) == 1
    assert repos.workspaces_opened == 1
    assert len(model.models_used) == calls_after_first_run
    assert len(tracker.comments_on("GR-100")) == 1
    assert len(tracker.comments_on("GR-101")) == 1


def test_the_branch_names_the_first_fix_that_passed_so_a_retry_does_not_collide(
    tmp_path,
):
    context, tracker, repos, _ = make_context(
        tmp_path,
        {
            "cheap-model": [
                *toggles("a.py", 3),
                *fix_of("b.py", "Fix b"),
                *fix_of("a.py", "Fix a"),
            ],
            "strong-model": toggles("a.py", 3),
        },
        files={"a.py": BUGGY, "b.py": BUGGY},
        file="a.py",
        settings=Settings(step_cap=3),
        extra_tickets=[{"key": "GR-101", "file": "b.py"}],
    )

    first = run(context)

    assert first.outcomes == {"GR-100": "failed", "GR-101": "fixed"}
    [pr_one] = repos.pull_requests
    assert pr_one.head == "gozu/fix-shared-gr-101"

    tracker.remove_label("GR-100", "veil-failed-fix")
    second = run(context)

    assert second.outcomes == {"GR-100": "fixed", "GR-101": "skipped"}
    pr_one, pr_two = repos.pull_requests
    assert pr_two.head == "gozu/fix-shared-gr-100"
    assert repos.commit_subjects_on(pr_two) == ["Fix a"]
