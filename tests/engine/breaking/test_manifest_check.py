import time

import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import make_context
from veil.engine import run

PACKAGE = """{
  "name": "app",
  "engines": {"node": ">=18"},
  "dependencies": {"left-pad": "^1.2.0", "zero": "0.3.1", "tiny": "~2.0.1"},
  "devDependencies": {"jest": "^29.0.0"}
}
"""

PYPROJECT = """[project]
name = "app"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "rich[jupyter]==13.1.0",
    "pytz",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
"""

REQUIREMENTS = """# pinned
requests==1.2.0
flask>=2.0  # web
-r other.txt
"""


def major(name, path, old, new):
    return (
        f"The dependency `{name}` in {path} goes from {old} to {new}. "
        "A version change of this size can break the code that uses it."
    )


def runtime(name, path, old, new):
    return (
        f"The `{name}` version that {path} requires goes from {old} to {new}. "
        "A user on an older version can fail."
    )


def removed(name, path):
    return (
        f"The dependency `{name}` is removed from {path}. "
        "The code that uses it can fail."
    )


def run_with(tmp_path, path, source, old, new):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [[edit_file(path, old, new)], [finish("Short explanation.")]],
        files={path: source},
        file=path,
        line=1,
    )
    report = run(context)
    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    return report, tracker, pr


@pytest.mark.parametrize(
    ("path", "source", "old", "new", "reason"),
    [
        (
            "package.json",
            PACKAGE,
            '"left-pad": "^1.2.0"',
            '"left-pad": "^2.0.0"',
            major("left-pad", "package.json", "^1.2.0", "^2.0.0"),
        ),
        (
            "package.json",
            PACKAGE,
            '"zero": "0.3.1"',
            '"zero": "0.4.0"',
            major("zero", "package.json", "0.3.1", "0.4.0"),
        ),
        (
            "package.json",
            PACKAGE,
            '"jest": "^29.0.0"',
            '"jest": "^30.0.0"',
            major("jest", "package.json", "^29.0.0", "^30.0.0"),
        ),
        (
            "package.json",
            PACKAGE,
            '"node": ">=18"',
            '"node": ">=20"',
            runtime("node", "package.json", ">=18", ">=20"),
        ),
        (
            "package.json",
            PACKAGE,
            '"left-pad": "^1.2.0", ',
            "",
            removed("left-pad", "package.json"),
        ),
        (
            "pyproject.toml",
            PYPROJECT,
            '"requests>=2.31"',
            '"requests>=3.0"',
            major("requests", "pyproject.toml", ">=2.31", ">=3.0"),
        ),
        (
            "pyproject.toml",
            PYPROJECT,
            "==13.1.0",
            "==14.0.0",
            major("rich", "pyproject.toml", "==13.1.0", "==14.0.0"),
        ),
        (
            "pyproject.toml",
            PYPROJECT,
            'requires-python = ">=3.10"',
            'requires-python = ">=3.12"',
            runtime("requires-python", "pyproject.toml", ">=3.10", ">=3.12"),
        ),
        (
            "pyproject.toml",
            PYPROJECT,
            '    "pytz",\n',
            "",
            removed("pytz", "pyproject.toml"),
        ),
        (
            "requirements.txt",
            REQUIREMENTS,
            "requests==1.2.0",
            "requests==2.0.0",
            major("requests", "requirements.txt", "==1.2.0", "==2.0.0"),
        ),
        (
            "requirements.txt",
            REQUIREMENTS,
            "flask>=2.0  # web\n",
            "",
            removed("flask", "requirements.txt"),
        ),
    ],
    ids=[
        "npm-range-major",
        "npm-zero-minor",
        "npm-dev-dependency-major",
        "npm-engines-raised",
        "npm-dependency-removed",
        "toml-range-major",
        "toml-pinned-major-with-extras",
        "toml-requires-python-raised",
        "toml-dependency-removed",
        "requirements-pinned-major",
        "requirements-dependency-removed",
    ],
)
def test_a_risky_manifest_change_flags_the_fix_even_when_the_model_says_no(
    tmp_path, path, source, old, new, reason
):
    report, tracker, pr = run_with(tmp_path, path, source, old, new)

    assert tracker.labels_on("GR-100") == ["breaking-change"]
    assert f"**Breaking change**\n{reason}\n\n" in pr.body
    assert report.breaking["GR-100"] == reason
    assert len(reason.replace("`", "").split()) <= 25


@pytest.mark.parametrize(
    ("path", "source", "old", "new"),
    [
        ("package.json", PACKAGE, '"left-pad": "^1.2.0"', '"left-pad": "^1.9.3"'),
        ("package.json", PACKAGE, '"tiny": "~2.0.1"', '"tiny": "~2.0.9"'),
        ("package.json", PACKAGE, '"node": ">=18"', '"node": ">=16"'),
        ("package.json", PACKAGE, '"name": "app"', '"name": "app", "version": "2.0.0"'),
        (
            "package.json",
            PACKAGE,
            '"jest": "^29.0.0"',
            '"jest": "^29.0.0", "eslint": "^9.0.0"',
        ),
        ("pyproject.toml", PYPROJECT, '"requests>=2.31"', '"requests>=2.40"'),
        ("pyproject.toml", PYPROJECT, '"pytz",', '"pytz", "six>=1.0",'),
        ("pyproject.toml", PYPROJECT, 'name = "app"', '# renamed\nname = "app"'),
        ("requirements.txt", REQUIREMENTS, "requests==1.2.0", "requests==1.9.0"),
        ("requirements.txt", REQUIREMENTS, "# pinned", "# pinned by hand"),
        ("requirements.txt", REQUIREMENTS, "flask>=2.0", "flask>=2.0\nclick>=8"),
    ],
    ids=[
        "npm-minor",
        "npm-patch",
        "npm-engines-lowered",
        "npm-own-version-changed",
        "npm-dependency-added",
        "toml-minor",
        "toml-dependency-added",
        "toml-comment",
        "requirements-minor",
        "requirements-comment",
        "requirements-dependency-added",
    ],
)
def test_a_safe_manifest_change_is_not_flagged(tmp_path, path, source, old, new):
    report, tracker, pr = run_with(tmp_path, path, source, old, new)

    assert tracker.labels_on("GR-100") == []
    assert "Breaking change" not in pr.body
    assert report.breaking == {}


@pytest.mark.parametrize(
    ("path", "source", "old", "new"),
    [
        ("package.json", "{not json", "{not json", '{"dependencies": {}}'),
        ("package.json", '{"dependencies": ["a"]}', '"a"', '"b"'),
        ("package.json", "[1, 2]", "1", "3"),
        (
            "pyproject.toml",
            "[project\nname = 1",
            "[project\nname = 1",
            "[project]\nname = 2",
        ),
        ("pyproject.toml", '[project]\ndependencies = "x"\n', '"x"', '"y"'),
        ("requirements.txt", "===\n!!!\n", "!!!", "???"),
    ],
    ids=[
        "json-invalid",
        "json-wrong-shape",
        "json-not-an-object",
        "toml-invalid",
        "toml-wrong-shape",
        "requirements-junk",
    ],
)
def test_a_manifest_that_does_not_parse_gives_no_flag_and_no_crash(
    tmp_path, path, source, old, new
):
    report, tracker, _ = run_with(tmp_path, path, source, old, new)

    assert tracker.labels_on("GR-100") == []
    assert report.breaking == {}


def test_a_manifest_reason_joins_the_model_reason_and_the_other_checks(tmp_path):
    context, _, _, _ = make_context(
        tmp_path,
        [
            [edit_file("package.json", '"^1.2.0"', '"^2.0.0"')],
            [
                finish(
                    "Short explanation.",
                    breaking=True,
                    breaking_reason="The build can fail.",
                )
            ],
        ],
        files={"package.json": PACKAGE},
        file="package.json",
        line=1,
    )

    report = run(context)

    assert report.breaking["GR-100"].startswith("The build can fail. The dependency")


NESTED = 5000


@pytest.mark.parametrize(
    ("path", "source", "new"),
    [
        ("package.json", "[" * NESTED + "1" + "]" * NESTED, '{"dependencies": {}}'),
        (
            "pyproject.toml",
            "a = " + "[" * NESTED + "]" * NESTED + "\n",
            '[project]\nname = "x"\n',
        ),
        ("app.py", "x = " + "-" * 100000 + "1\n", "x = 1\n"),
    ],
    ids=["json-nested", "toml-nested", "python-unary-chain"],
)
def test_a_hostile_file_before_the_fix_gives_no_flag_and_does_not_stop_the_run(
    tmp_path, path, source, new
):
    report, tracker, _ = run_with(tmp_path, path, source, source, new)

    assert tracker.labels_on("GR-100") == []
    assert report.breaking == {}


def test_a_requirements_line_with_many_brackets_does_not_stall_the_check(tmp_path):
    source = "requests==1.2.0\nx" + "[" * 150000 + "\n"
    started = time.perf_counter()

    run_with(tmp_path, "requirements.txt", source, "requests==1.2.0", "requests==1.3.0")

    assert time.perf_counter() - started < 5
