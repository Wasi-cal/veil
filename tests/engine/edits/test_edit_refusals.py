import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import (
    FIXED,
    GOOD_EDIT,
    VULNERABLE,
    make_context,
)
from veil.engine import run

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
