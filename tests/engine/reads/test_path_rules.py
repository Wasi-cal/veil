import pytest

from veil.engine.errors.rule_violation import RuleViolation
from veil.engine.workspace.path_rules import check_editable, check_readable


@pytest.mark.parametrize(
    "path",
    [
        ".git/config",
        ".GIT/config",
        ".Git/hooks/pre-commit",
        "sub/.git/config",
        "sub/.GIT/config",
        ".github/workflows/ci.yml",
        ".GITHUB/Workflows/ci.yml",
        "sub/.github/CODEOWNERS",
        ".github\\workflows\\ci.yml",
    ],
)
def test_the_folders_git_and_github_are_refused_in_any_case_and_at_any_depth(path):
    """A Linux git repo cannot hold `.GIT/config`, so the end-to-end tests cannot cover that case."""
    with pytest.raises(RuleViolation):
        check_readable(path)
    with pytest.raises(RuleViolation):
        check_editable(path)


@pytest.mark.parametrize("path", ["app.py", "src/github/app.py", "docs/git-notes.md"])
def test_a_name_that_only_looks_like_git_or_github_is_allowed(path):
    assert check_readable(path) == path
    assert check_editable(path) == path
