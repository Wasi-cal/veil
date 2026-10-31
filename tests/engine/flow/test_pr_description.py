from tests.fakes import edit_file, finish
from tests.support.scenario import make_context
from veil.engine import run

PROBLEM = "The function run_expression sends user text to eval. An attacker can run any code on the server."
CHANGE = "The function now calls ast.literal_eval. It accepts only Python literals."
SOLVES = "A request can no longer run code. Bad input raises an error."


def finish_with_parts():
    return finish(CHANGE, problem=PROBLEM, solves=SOLVES)


def run_one(tmp_path, finish_call, **ticket):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [[edit_file("app.py", "eval(input())", "int(input())")], [finish_call]],
        **ticket,
    )
    report = run(context)
    return report, tracker, repos


def test_the_pr_says_why_it_is_a_problem_what_changed_and_what_it_solves(tmp_path):
    _, _, repos = run_one(tmp_path, finish_with_parts())

    [pr] = repos.pull_requests
    assert "GR-100" in pr.body
    assert f"Why this is a problem: {PROBLEM}" in pr.body
    assert f"What changed: {CHANGE}" in pr.body
    assert f"What this solves: {SOLVES}" in pr.body
    assert pr.body.index("Why this is a problem") < pr.body.index("What changed")
    assert pr.body.index("What changed") < pr.body.index("What this solves")


def test_the_comment_on_the_ticket_has_the_same_three_parts(tmp_path):
    _, tracker, _ = run_one(tmp_path, finish_with_parts())

    [comment] = tracker.comments_on("GR-100")
    assert f"Why this is a problem: {PROBLEM}" in comment
    assert f"What changed: {CHANGE}" in comment
    assert f"What this solves: {SOLVES}" in comment
    assert "pull/" in comment


def test_a_problem_that_copies_the_text_of_the_ticket_is_refused_and_the_model_tries_again(
    tmp_path,
):
    copied = finish(
        CHANGE,
        problem="Avoid eval on user input.",
        solves=SOLVES,
    )
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", "eval(input())", "int(input())")],
            [copied],
            [finish_with_parts()],
        ],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert PROBLEM in pr.body
    assert "Avoid eval on user input." not in pr.body


def test_a_part_that_is_empty_is_refused_and_the_model_tries_again(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", "eval(input())", "int(input())")],
            [finish(CHANGE, problem="  ", solves=SOLVES)],
            [finish_with_parts()],
        ],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert PROBLEM in repos.pull_requests[0].body


def test_a_shared_pr_with_two_fixes_gives_each_ticket_its_own_three_parts(tmp_path):
    other = (
        "The helper parse_value passes text to eval.",
        "It now parses a number.",
        "Bad text cannot run code.",
    )
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("a.py", "eval(input())", "int(input())")],
            [finish(CHANGE, problem=PROBLEM, solves=SOLVES)],
            [edit_file("b.py", "eval(input())", "int(input())")],
            [finish(other[1], problem=other[0], solves=other[2])],
        ],
        files={"a.py": "value = eval(input())\n", "b.py": "value = eval(input())\n"},
        file="a.py",
        severity="Medium",
        extra_tickets=[{"key": "GR-101", "file": "b.py", "severity": "Low"}],
    )

    run(context)

    [pr] = repos.pull_requests
    assert pr.body.count("Why this is a problem:") == 2
    assert pr.body.index("GR-100") < pr.body.index(PROBLEM) < pr.body.index("GR-101")
    assert other[0] in pr.body
