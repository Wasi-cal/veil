import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import (
    assert_failed_fix,
    both_attempts,
    make_context,
)
from veil.engine import run


@pytest.mark.parametrize(
    ("path", "before", "old", "new"),
    [
        ("app.py", "value = 1\n", "value = 1", "value = ("),
        ("config.json", '{"a": 1}\n', '{"a": 1}', '{"a": 1,'),
        ("pyproject.toml", "a = 1\n", "a = 1", "a = "),
    ],
    ids=["python", "json", "toml"],
)
def test_edited_file_that_no_longer_parses_is_a_failed_fix(
    tmp_path, path, before, old, new
):
    context, tracker, repos, _ = make_context(
        tmp_path,
        both_attempts([[edit_file(path, old, new)], [finish("Edited.")]]),
        files={path: before},
        file=path,
        line=1,
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert path in comment


def test_file_that_is_broken_in_the_middle_but_parses_at_finish_is_fixed(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", "value = 1", "value = (")],
            [edit_file("app.py", "value = (", "value = 2")],
            [finish("Edited.")],
        ],
        files={"app.py": "value = 1\n"},
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert len(repos.pull_requests) == 1


def test_edited_file_of_unknown_type_is_not_parsed(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        [[edit_file("notes.txt", "ok", "this ( is { not code")], [finish("Edited.")]],
        files={"notes.txt": "ok\n"},
        file="notes.txt",
        line=1,
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert len(repos.pull_requests) == 1


def test_deeply_nested_json_is_a_failed_fix_not_a_crash(tmp_path):
    depth = 100_000
    context, tracker, repos, _ = make_context(
        tmp_path,
        both_attempts(
            [
                [edit_file("data.json", "[]", "[" * depth + "]" * depth)],
                [finish("Edited.")],
            ]
        ),
        files={"data.json": "[]\n"},
        file="data.json",
        line=1,
    )

    report = run(context)

    assert_failed_fix(tracker, repos, report)
