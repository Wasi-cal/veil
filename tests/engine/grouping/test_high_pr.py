from tests.engine.grouping.test_shared_pr import BUGGY, FIXED_LINE, fix_of
from tests.fakes import edit_file, finish
from tests.support.scenario import both_attempts, make_context
from veil.engine import run


def edit_file_a(old, new):
    return edit_file("a.py", old, new)


def finish_message(commit_message):
    return finish("Fixed one line.", commit_message=commit_message)


def test_each_high_ticket_gets_its_own_high_pr(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a"), *fix_of("b.py", "Fix b")],
        files={"a.py": BUGGY, "b.py": BUGGY},
        file="a.py",
        severity="High",
        extra_tickets=[{"key": "GR-101", "file": "b.py"}],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed", "GR-101": "fixed"}
    first, second = repos.pull_requests
    assert first.head != second.head
    assert repos.commit_subjects_on(first) == ["Fix a"]
    assert repos.commit_subjects_on(second) == ["Fix b"]
    assert first.url in tracker.comments_on("GR-100")[0]
    assert second.url in tracker.comments_on("GR-101")[0]


def test_high_fixes_of_the_same_file_go_into_one_pr_and_the_body_gives_the_reason(
    tmp_path,
):
    two_bugs = "first = eval(input())\nsecond = eval(input())\n"
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [
                edit_file_a("first = eval(input())", "first = int(input())"),
                finish_message("Fix first"),
            ],
            [
                edit_file_a("second = eval(input())", "second = int(input())"),
                finish_message("Fix second"),
            ],
        ],
        files={"a.py": two_bugs},
        file="a.py",
        severity="High",
        extra_tickets=[{"key": "GR-101", "line": 2}],
        line=1,
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed", "GR-101": "fixed"}
    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == ["Fix first", "Fix second"]
    assert repos.file_on(pr, "a.py") == "first = int(input())\nsecond = int(input())\n"
    assert "same file" in pr.body
    assert "a.py" in pr.body
    assert FIXED_LINE not in pr.body


def test_high_tickets_of_the_same_file_group_even_if_the_path_is_written_differently(
    tmp_path,
):
    two_bugs = "first = eval(input())\nsecond = eval(input())\n"
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [
                edit_file_a("first = eval(input())", "first = int(input())"),
                finish_message("Fix first"),
            ],
            [
                edit_file_a("second = eval(input())", "second = int(input())"),
                finish_message("Fix second"),
            ],
        ],
        files={"a.py": two_bugs},
        file="./a.py",
        severity="High",
        extra_tickets=[{"key": "GR-101", "file": "a.py", "line": 2}],
        line=1,
    )

    run(context)

    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == ["Fix first", "Fix second"]


def test_the_body_gives_no_same_file_reason_if_only_one_high_fix_passed(tmp_path):
    two_bugs = "first = eval(input())\nsecond = eval(input())\n"
    context, _, repos, _ = make_context(
        tmp_path,
        both_attempts(
            [
                [
                    edit_file_a("first = eval(input())", "first = int(input())"),
                    finish_message("Fix first"),
                ],
                [finish("Nothing to do.")],
                [finish("Nothing to do.")],
            ]
        ),
        files={"a.py": two_bugs},
        file="a.py",
        severity="High",
        extra_tickets=[{"key": "GR-101", "line": 2}],
        line=1,
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed", "GR-101": "failed"}
    [pr] = repos.pull_requests
    assert "same file" not in pr.body
