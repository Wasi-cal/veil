from tests.fakes import edit_file, finish
from tests.support.scenario import CHEAP, STRONG, make_context
from veil.engine import FixQuery, Settings, run

BUGGY = "value = eval(input())\n"
FIXED_LINE = "value = int(input())\n"


def fix_of(path, commit_message):
    """The script of one ticket: edit one file and finish."""
    return [
        [edit_file(path, "eval(input())", "int(input())")],
        [finish(f"Changed {path}.", commit_message=commit_message)],
    ]


def test_tickets_of_different_files_get_one_pr_each_whatever_the_severity(tmp_path):
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
    first, second = repos.pull_requests
    assert report.pull_requests == [first.url, second.url]
    assert first.head != second.head
    assert first.draft is False
    assert first.base == second.base == "feature"
    assert repos.commit_subjects_on(first) == ["fix(security): Fix a"]
    assert repos.commit_subjects_on(second) == ["fix(security): Fix b"]
    assert repos.file_on(first, "a.py") == FIXED_LINE
    assert repos.file_on(second, "b.py") == FIXED_LINE
    assert repos.workspaces_opened == 2
    for key, label, pr in (
        ("GR-100", "issue-gr-100", first),
        ("GR-101", "issue-gr-101", second),
    ):
        assert pr.url in tracker.comments_on(key)[0]
        assert tracker.status_of(key) == "In Review"
        query = FixQuery(
            repo="acme/app",
            issue_label=label,
            source_branch="feature",
            branch_prefix="veil/fix-",
        )
        assert repos.find_existing_fix(query) == "open_pr"


def toggles(path, count):
    """`count` valid edits of one file that never finish."""
    pairs = [("eval(input())", "int(input())"), ("int(input())", "eval(input())")]
    return [[edit_file(path, *pairs[n % 2])] for n in range(count)]


def test_a_failed_fix_gets_no_pr_and_leaves_no_edit(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path,
        {
            CHEAP: [
                *fix_of("a.py", "Fix a"),
                *toggles("b.py", 3),
                *fix_of("c.py", "Fix c"),
            ],
            STRONG: toggles("b.py", 3),
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
    first, second = repos.pull_requests
    assert repos.commit_subjects_on(first) == ["fix(security): Fix a"]
    assert repos.commit_subjects_on(second) == ["fix(security): Fix c"]
    assert repos.changed_paths_on(first) == {"a.py"}
    assert repos.changed_paths_on(second) == {"c.py"}
    assert repos.file_on(first, "b.py") == BUGGY
    assert repos.file_on(second, "b.py") == BUGGY
    assert tracker.labels_on("GR-101") == ["veil-failed-fix"]
    assert tracker.status_of("GR-101") == "To Do"
    assert tracker.labels_on("GR-100") == []


def test_there_is_no_cap_on_the_number_of_prs(tmp_path):
    count = 11
    context, _, repos, _ = make_context(
        tmp_path,
        [step for n in range(count) for step in fix_of(f"f{n}.py", f"Fix {n}")],
        files={f"f{n}.py": BUGGY for n in range(count)},
        file="f0.py",
        extra_tickets=[
            {"key": f"GR-{100 + n}", "file": f"f{n}.py"} for n in range(1, count)
        ],
    )

    report = run(context)

    assert set(report.outcomes.values()) == {"fixed"}
    assert len(report.outcomes) == count
    assert len(repos.pull_requests) == count
    assert len({pr.head for pr in repos.pull_requests}) == count
    assert all(len(repos.commit_subjects_on(pr)) == 1 for pr in repos.pull_requests)


def test_tickets_of_different_source_prs_get_separate_prs(tmp_path):
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
    assert repos.commit_subjects_on(first) in (
        ["fix(security): Fix a"],
        ["fix(security): Fix b"],
    )


def test_a_second_run_after_the_prs_creates_nothing(tmp_path):
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
    assert len(repos.pull_requests) == 2
    assert repos.workspaces_opened == 2
    assert len(model.models_used) == calls_after_first_run
    assert len(tracker.comments_on("GR-100")) == 1
    assert len(tracker.comments_on("GR-101")) == 1


def test_the_branch_names_the_first_fix_that_passed_so_a_retry_does_not_collide(
    tmp_path,
):
    context, tracker, repos, _ = make_context(
        tmp_path,
        {
            CHEAP: [
                *toggles("a.py", 3),
                *fix_of("b.py", "Fix b"),
                *fix_of("a.py", "Fix a"),
            ],
            STRONG: toggles("a.py", 3),
        },
        files={"a.py": BUGGY, "b.py": BUGGY},
        file="a.py",
        settings=Settings(step_cap=3),
        extra_tickets=[{"key": "GR-101", "file": "b.py"}],
    )

    first = run(context)

    assert first.outcomes == {"GR-100": "failed", "GR-101": "fixed"}
    [pr_one] = repos.pull_requests
    assert pr_one.head == "veil/fix-gr-101"

    tracker.remove_label("GR-100", "veil-failed-fix")
    second = run(context)

    assert second.outcomes == {"GR-100": "fixed", "GR-101": "skipped"}
    pr_one, pr_two = repos.pull_requests
    assert pr_two.head == "veil/fix-gr-100"
    assert repos.commit_subjects_on(pr_two) == ["fix(security): Fix a"]
