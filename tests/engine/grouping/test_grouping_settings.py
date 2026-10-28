import pytest
from pydantic import ValidationError

from tests.engine.grouping.test_shared_pr import BUGGY, fix_of
from tests.support.scenario import make_context
from veil.engine import Settings, run


def three_tickets(tmp_path, severities, settings=None):
    """Three tickets of one Source PR. Each one has its own file and its own severity word."""
    first, second, third = severities
    return make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a"), *fix_of("b.py", "Fix b"), *fix_of("c.py", "Fix c")],
        files={"a.py": BUGGY, "b.py": BUGGY, "c.py": BUGGY},
        file="a.py",
        severity=first,
        settings=settings,
        extra_tickets=[
            {"key": "GR-101", "file": "b.py", "severity": second},
            {"key": "GR-102", "file": "c.py", "severity": third},
        ],
    )


def pr_sizes(repos):
    """The number of commits of each PR, as a sorted list."""
    return sorted(len(repos.commit_subjects_on(pr)) for pr in repos.pull_requests)


@pytest.mark.parametrize(
    ("severities", "sizes"),
    [
        (("BLOCKER", "MAJOR", "MINOR"), [1, 2]),
        (("CRITICAL", "INFO", "Low"), [1, 2]),
        (("High", "Medium", "Low"), [1, 2]),
        (("MAJOR", "MINOR", "info"), [3]),
        (("WEIRD", "MAJOR", "MINOR"), [1, 2]),
    ],
    ids=[
        "sonar-names",
        "other-sonar-names",
        "plain-words",
        "all-low-or-medium",
        "unknown-is-high",
    ],
)
def test_default_severity_map_sends_high_to_its_own_pr_and_unknown_words_are_high(
    tmp_path, severities, sizes
):
    context, _, repos, _ = three_tickets(tmp_path, severities)

    run(context)

    assert pr_sizes(repos) == sizes


def test_the_severity_map_is_a_setting(tmp_path):
    settings = Settings(severity_map={"MAJOR": "high", "MINOR": "low"})
    context, _, repos, _ = three_tickets(
        tmp_path, ("MAJOR", "MINOR", "MINOR"), settings
    )

    run(context)

    assert pr_sizes(repos) == [1, 2]


def test_the_branch_prefix_is_a_setting_and_the_no_loop_rule_uses_it(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a")],
        files={"a.py": BUGGY},
        file="a.py",
        settings=Settings(branch_prefix="veil/"),
        extra_tickets=[{"key": "GR-101", "file": "a.py", "branch": "veil/earlier"}],
    )

    report = run(context)

    [pr] = repos.pull_requests
    assert pr.head.startswith("veil/")
    assert report.skipped == {"raised_against_fix_branch": ["GR-101"]}


def test_a_partial_severity_map_changes_only_its_words_and_keeps_the_defaults(tmp_path):
    settings = Settings(severity_map={"MAJOR": "high"})
    context, _, repos, _ = three_tickets(tmp_path, ("MAJOR", "MINOR", "INFO"), settings)

    run(context)

    assert pr_sizes(repos) == [1, 2]


@pytest.mark.parametrize("bad", ["", "a", "gozu", "x/", "gozu fix/"])
def test_the_branch_prefix_must_be_long_enough_and_end_with_a_separator(bad):
    with pytest.raises(ValidationError):
        Settings(branch_prefix=bad)
