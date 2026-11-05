import pytest
from pydantic import ValidationError

from tests.engine.grouping.test_one_pr_per_ticket import BUGGY, fix_of
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


def opened_in_order(repos):
    """The ticket key of each PR, in the order in which veil opened the PRs. The title starts with the key."""
    return [pr.title.split(" | ", 1)[0] for pr in repos.pull_requests]


def keys(*names):
    """The key of the ticket of each file: a is GR-100, b is GR-101 and c is GR-102."""
    return [f"GR-{100 + ord(name) - ord('a')}" for name in names]


@pytest.mark.parametrize(
    ("severities", "order"),
    [
        (("MINOR", "BLOCKER", "MAJOR"), ("b", "c", "a")),
        (("Low", "High", "Medium"), ("b", "c", "a")),
        (("MAJOR", "MINOR", "WEIRD"), ("c", "a", "b")),
        (("INFO", "info", "MINOR"), ("a", "b", "c")),
    ],
    ids=["sonar-names", "plain-words", "unknown-is-high", "ties-keep-ticket-order"],
)
def test_every_ticket_gets_its_own_pr_and_high_severity_goes_first(
    tmp_path, severities, order
):
    context, _, repos, _ = three_tickets(tmp_path, severities)

    run(context)

    assert len(repos.pull_requests) == 3
    assert opened_in_order(repos) == keys(*order)


def test_the_severity_map_is_a_setting_and_changes_the_order(tmp_path):
    settings = Settings(severity_map={"BLOCKER": "low", "MAJOR": "high"})
    context, _, repos, _ = three_tickets(
        tmp_path, ("MAJOR", "BLOCKER", "MINOR"), settings
    )

    run(context)

    assert opened_in_order(repos) == keys("a", "b", "c")


def test_a_partial_severity_map_changes_only_its_words_and_keeps_the_defaults(tmp_path):
    settings = Settings(severity_map={"MAJOR": "high"})
    context, _, repos, _ = three_tickets(
        tmp_path, ("MINOR", "MAJOR", "BLOCKER"), settings
    )

    run(context)

    assert opened_in_order(repos) == keys("b", "c", "a")


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


def test_a_custom_prefix_does_not_weaken_the_no_loop_rule_for_the_fixed_prefix(
    tmp_path,
):
    context, _, repos, _ = make_context(
        tmp_path,
        [*fix_of("a.py", "Fix a")],
        files={"a.py": BUGGY},
        file="a.py",
        settings=Settings(branch_prefix="veil/"),
        extra_tickets=[{"key": "GR-101", "file": "a.py", "branch": "veil/fix-earlier"}],
    )

    report = run(context)

    assert report.skipped == {"raised_against_fix_branch": ["GR-101"]}
    assert len(repos.pull_requests) == 1


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "a",
        "gozu",
        "x/",
        "gozu fix/",
        "---",
        "../",
        "-x-",
        "a..b/",
        "a//b/",
        "a/.b/",
    ],
)
def test_the_branch_prefix_must_be_long_enough_and_end_with_a_separator(bad):
    with pytest.raises(ValidationError):
        Settings(branch_prefix=bad)
