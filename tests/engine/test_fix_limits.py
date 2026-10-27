import pytest

from tests.engine.support import (
    EDIT_THEN_FINISH,
    FIXED,
    GOOD_EDIT,
    VULNERABLE,
    assert_failed_fix,
    make_context,
    toggle_edits,
)
from tests.fakes import edit_file, finish
from veil.engine import Settings, run


def test_attempt_that_reaches_the_step_cap_is_a_failed_fix(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path, toggle_edits(5), settings=Settings(step_cap=3)
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert "step" in comment.lower()


def test_attempt_that_finishes_on_the_last_allowed_step_is_fixed(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path, EDIT_THEN_FINISH, settings=Settings(step_cap=2)
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert len(repos.pull_requests) == 1
    assert tracker.labels_on("GR-100") == []


FIVE_LINES = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n"


def test_edit_that_would_cross_the_diff_limit_is_rejected(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", "a = 1\nb = 2\n", "a = 10\nb = 20\n")],
            [edit_file("app.py", "e = 5", "e = 50")],
            [finish("Changed e.")],
        ],
        files={"app.py": FIVE_LINES},
        settings=Settings(diff_limit=1),
    )

    report = run(context)

    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == "a = 1\nb = 2\nc = 3\nd = 4\ne = 50\n"
    assert report.outcomes == {"GR-100": "fixed"}


WORKFLOW = ".github/workflows/ci.yml"


@pytest.mark.parametrize(
    ("extra_files", "bad_edit"),
    [
        pytest.param(
            {WORKFLOW: "name: ci\n"},
            edit_file(WORKFLOW, "name: ci", "name: evil"),
            id="workflow",
        ),
        pytest.param(
            {"uv.lock": "version = 1\n"},
            edit_file("uv.lock", "version = 1", "version = 2"),
            id="lockfile",
        ),
        pytest.param(
            {"web/package-lock.json": "{}\n"},
            edit_file("web/package-lock.json", "{}", '{"a": 1}'),
            id="nested-lockfile",
        ),
        pytest.param(
            {}, edit_file("../evil.txt", "", "owned"), id="outside-repo-relative"
        ),
        pytest.param(
            {}, edit_file("/etc/evil.txt", "", "owned"), id="outside-repo-absolute"
        ),
        pytest.param({}, edit_file("new_file.py", "", "print(1)"), id="new-file"),
        pytest.param({}, edit_file("app.py", VULNERABLE, ""), id="deletion"),
        pytest.param(
            {}, edit_file("app.py", VULNERABLE, "\n"), id="deletion-newline-only"
        ),
        pytest.param(
            {},
            edit_file("app.py", VULNERABLE, " \n\t\n"),
            id="deletion-whitespace-only",
        ),
        pytest.param(
            {WORKFLOW: "name: ci\n"},
            edit_file(".GITHUB/Workflows/ci.yml", "name: ci", "name: evil"),
            id="workflow-upper-case",
        ),
        pytest.param(
            {WORKFLOW: "name: ci\n"},
            edit_file(".github\\workflows\\ci.yml", "name: ci", "name: evil"),
            id="workflow-backslashes",
        ),
        pytest.param(
            {}, edit_file("..\\evil.txt", "", "owned"), id="outside-repo-backslash"
        ),
        pytest.param(
            {".env": "KEY=1\n"},
            edit_file(".env", "KEY=1", "KEY=2"),
            id="secret-file",
        ),
        pytest.param(
            {"keys/id_rsa": "PRIVATE\n"},
            edit_file("keys/id_rsa", "PRIVATE", "PUBLIC"),
            id="private-key",
        ),
    ],
)
def test_refused_edit_changes_nothing_and_the_model_is_told(
    tmp_path, extra_files, bad_edit
):
    context, _, repos, _ = make_context(
        tmp_path,
        [[bad_edit], [GOOD_EDIT], [finish("Fixed.")]],
        files={"app.py": VULNERABLE, **extra_files},
    )

    run(context)

    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED
    for path, content in extra_files.items():
        assert repos.file_on(pr, path) == content
    assert repos.changed_paths_on(pr) == {"app.py"}
    assert not (tmp_path / "clone" / "0" / "acme" / "evil.txt").exists()


THREE_LINES = "a = 1\nb = 2\nc = 3\n"


@pytest.mark.parametrize(
    "new",
    ["a = 1\r\nb = 2\r\nc = 3\r\n", "a = 1  \nb = 2  \nc = 3  \n"],
    ids=["line-endings", "trailing-spaces"],
)
def test_edit_that_only_changes_line_endings_or_trailing_spaces_counts_as_changed_lines(
    tmp_path, new
):
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", THREE_LINES, new)],
            [edit_file("app.py", "c = 3", "c = 30")],
            [finish("Changed c.")],
        ],
        files={"app.py": THREE_LINES},
        settings=Settings(diff_limit=2),
    )

    run(context)

    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == "a = 1\nb = 2\nc = 30\n"
