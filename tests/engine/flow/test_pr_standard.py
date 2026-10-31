import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import make_context
from veil.engine import run

GOOD = "fix(security): replace eval with int"


def finish_call(commit_message):
    return finish("The call is now int.", commit_message=commit_message, prefix=False)


def run_with(tmp_path, scripts, **ticket):
    context, tracker, repos, _ = make_context(tmp_path, scripts, **ticket)
    report = run(context)
    return report, tracker, repos


FIRST = [edit_file("app.py", "eval(input())", "int(input())")]


@pytest.mark.parametrize(
    "bad",
    [
        "Replace eval with int",
        "fix: replace eval with int",
        "fix(security):replace eval",
        "fix(security): replace eval with int.",
        "fix(security): " + "x" * 80,
        "feat(security): replace eval with int",
    ],
)
def test_a_commit_message_that_is_not_a_conventional_security_fix_is_refused_and_the_model_tries_again(
    tmp_path, bad
):
    report, _, repos = run_with(
        tmp_path, [FIRST, [finish_call(bad)], [finish_call(GOOD)]]
    )

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == [GOOD]


def test_the_commit_names_its_ticket_in_a_footer(tmp_path):
    _, _, repos = run_with(tmp_path, [FIRST, [finish_call(GOOD)]])

    [pr] = repos.pull_requests
    [message] = repos.commit_messages_on(pr)
    assert message.strip().splitlines() == [GOOD, "", "Refs: GR-100"]


def test_the_pr_title_is_the_commit_subject_and_the_ticket_key(tmp_path):
    _, _, repos = run_with(tmp_path, [FIRST, [finish_call(GOOD)]])

    [pr] = repos.pull_requests
    assert pr.title == f"{GOOD} (GR-100)"


def test_the_title_of_a_shared_pr_counts_the_findings_and_names_the_tickets(tmp_path):
    scripts = [
        [edit_file("a.py", "eval(input())", "int(input())")],
        [finish_call("fix(security): replace eval in a")],
        [edit_file("b.py", "eval(input())", "int(input())")],
        [finish_call("fix(security): replace eval in b")],
    ]
    _, _, repos = run_with(
        tmp_path,
        scripts,
        files={"a.py": "value = eval(input())\n", "b.py": "value = eval(input())\n"},
        file="a.py",
        severity="Medium",
        extra_tickets=[{"key": "GR-101", "file": "b.py", "severity": "Low"}],
    )

    [pr] = repos.pull_requests
    assert pr.title == "fix(security): resolve 2 findings (GR-100, GR-101)"


def test_the_body_has_one_section_for_each_ticket_and_no_empty_summary(tmp_path):
    _, _, repos = run_with(
        tmp_path,
        [
            FIRST,
            [
                finish(
                    "The call is now int.",
                    commit_message=GOOD,
                    problem="Text reaches eval, so it can run code.",
                    solves="Text can no longer run code.",
                )
            ],
        ],
    )

    [pr] = repos.pull_requests
    assert pr.body.startswith("## GR-100 · `app.py:3`")
    assert "## Summary" not in pr.body
    assert "draft" not in pr.body.lower()
    assert "## GR-100 · `app.py:3`" in pr.body
    section = pr.body.split("## GR-100 · `app.py:3`")[1]
    assert section.index("**Why this is a problem**") < section.index(
        "**What changed**"
    )
    assert section.index("**What changed**") < section.index("**What this solves**")
    assert "Text reaches eval, so it can run code." in section
