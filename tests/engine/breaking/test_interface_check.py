import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import make_context
from veil.engine import run

SOURCE = """def parse(text):
    return int(text)


def convert(text, base=10):
    return int(text, base)


class Parser:
    def run(self, text):
        return parse(text)

    def _step(self):
        return 1


def _helper(a):
    return a
"""

REMOVED = "The public function `parse` in app.py is removed or renamed."
RENAMED_METHOD = "The public method `Parser.run` in app.py is removed or renamed."
REMOVED_CLASS = "The public class `Parser` in app.py is removed or renamed."


def changed(name):
    return (
        f"The parameters of the public function `{name}` in app.py changed. "
        "A caller that works now can fail."
    )


CHANGED = changed("parse")


def run_with(tmp_path, edits, source=SOURCE, **finish_fields):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", old, new) for old, new in edits],
            [finish("Short explanation.", **finish_fields)],
        ],
        files={"app.py": source},
        line=1,
    )
    report = run(context)
    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    return report, tracker, pr


@pytest.mark.parametrize(
    ("edits", "reason"),
    [
        ([("def parse(text):\n    return int(text)\n\n\n", "")], REMOVED),
        ([("def parse(text)", "def parse_text(text)")], REMOVED),
        ([("def run(self, text)", "def execute(self, text)")], RENAMED_METHOD),
        ([("class Parser:", "class Reader:")], REMOVED_CLASS),
        ([("def parse(text)", "def parse(text, base)")], CHANGED),
        ([("def parse(text)", "def parse(data)")], CHANGED),
        ([("def parse(text)", "def parse()")], CHANGED),
        ([("def parse(text)", "def parse(base=10, text=None)")], CHANGED),
        ([("def parse(text)", "def parse(*, text)")], CHANGED),
        (
            [("def convert(text, base=10)", "def convert(text, base)")],
            changed("convert"),
        ),
    ],
    ids=[
        "function-removed",
        "function-renamed",
        "method-renamed",
        "class-renamed",
        "required-parameter-added",
        "parameter-renamed",
        "parameter-removed",
        "optional-parameter-before-old-one",
        "parameter-becomes-keyword-only",
        "default-removed",
    ],
)
def test_a_changed_public_interface_flags_the_fix_even_when_the_model_says_no(
    tmp_path, edits, reason
):
    report, tracker, pr = run_with(tmp_path, edits)

    assert tracker.labels_on("GR-100") == ["breaking-change"]
    assert f"**Breaking change**\n{reason}\n\n" in pr.body
    assert report.breaking["GR-100"] == reason


@pytest.mark.parametrize(
    "edits",
    [
        [("def _helper(a)", "def _helper_two(a)")],
        [("def _step(self)", "def _step(self, extra)")],
        [("def parse(text)", "def parse(text, base=10)")],
        [("def convert(text, base=10)", "def convert(text, base=10, *, strict=False)")],
        [("def parse(text)", "def parse(text, *rest, **options)")],
        [
            (
                "return int(text)\n\n\ndef convert",
                "return int(text.strip())\n\n\ndef convert",
            )
        ],
        [("def _helper(a):", "def extra(b):\n    return b\n\n\ndef _helper(a):")],
        [("def convert(text, base=10)", "def convert(text, base=16)")],
    ],
    ids=[
        "private-function-renamed",
        "private-method-parameters-changed",
        "optional-parameter-added-at-the-end",
        "optional-keyword-only-parameter-added",
        "var-parameters-added",
        "body-only",
        "public-function-added",
        "default-value-changed",
    ],
)
def test_a_change_that_keeps_the_public_interface_is_not_flagged(tmp_path, edits):
    report, tracker, pr = run_with(tmp_path, edits)

    assert tracker.labels_on("GR-100") == []
    assert "Breaking change" not in pr.body
    assert report.breaking == {}


def test_a_file_that_does_not_parse_before_the_fix_gives_no_flag_and_no_crash(tmp_path):
    report, tracker, _ = run_with(
        tmp_path,
        [("def parse(:\n", "def parse():\n")],
        source="def parse(:\n    pass\n",
    )

    assert tracker.labels_on("GR-100") == []
    assert report.breaking == {}


def test_a_file_that_is_not_python_is_not_checked(tmp_path):
    context, tracker, _, _ = make_context(
        tmp_path,
        [[edit_file("app.txt", "def a(x):", "def b(x):")], [finish("Done.")]],
        files={"app.txt": "def a(x):\n"},
        file="app.txt",
        line=1,
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert tracker.labels_on("GR-100") == []


def test_the_reason_of_the_model_comes_first_and_the_check_reason_follows(tmp_path):
    model_reason = "The caller of parse can pass a string."
    report, _, pr = run_with(
        tmp_path,
        [("def parse(text)", "def parse(text, base)")],
        breaking=True,
        breaking_reason=model_reason,
    )

    reasons = pr.body.split("**Breaking change**\n")[1].split("\n\n")[0].splitlines()
    assert reasons[0] == f"- {model_reason}"
    assert reasons[1].startswith("- The parameters of the public function `parse`")
    assert report.breaking["GR-100"].startswith(model_reason)


def test_at_most_five_reasons_show(tmp_path):
    names = [f"f{n}" for n in range(7)]
    source = "".join(f"def {name}(x):\n    return x\n\n\n" for name in names)
    _, _, pr = run_with(tmp_path, [(source, "VALUE = 1\n")], source=source)

    section = pr.body.split("**Breaking change**\n")[1].split("\n\n")[0]
    assert len(section.splitlines()) == 5
