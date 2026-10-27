import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import (
    make_context,
)
from veil.engine import Settings, run

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
