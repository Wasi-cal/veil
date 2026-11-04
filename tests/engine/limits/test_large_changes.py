import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import make_context
from veil.engine import SettingsError, parse_settings, run

THREE_LINES = "a = 1\nb = 2\nc = 3\n"


def numbered(count, name):
    return "".join(f"{name}{n} = {n}\n" for n in range(count))


@pytest.mark.parametrize("lines", [201, 1000])
def test_a_large_change_is_not_refused_for_its_size(tmp_path, lines):
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("data.py", numbered(lines, "a"), numbered(lines, "b"))],
            [finish("Renamed the values.")],
        ],
        files={"data.py": numbered(lines, "a")},
        file="data.py",
        line=1,
    )

    report = run(context)

    [pr] = repos.pull_requests
    assert repos.file_on(pr, "data.py") == numbered(lines, "b")
    assert report.outcomes == {"GR-100": "fixed"}


@pytest.mark.parametrize(
    "new",
    ["a = 1\r\nb = 2\r\nc = 3\r\n", "a = 1  \nb = 2  \nc = 3  \n"],
    ids=["line-endings", "trailing-spaces"],
)
def test_an_edit_that_only_changes_line_endings_or_trailing_spaces_is_a_change(
    tmp_path, new
):
    context, _, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", THREE_LINES, new)],
            [finish("Changed the white space.")],
        ],
        files={"app.py": THREE_LINES},
    )

    report = run(context)

    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == new
    assert report.outcomes == {"GR-100": "fixed"}


def test_the_diff_limit_is_not_a_setting_any_more():
    with pytest.raises(SettingsError, match="unknown setting diff_limit."):
        parse_settings({"diff_limit": 100})
