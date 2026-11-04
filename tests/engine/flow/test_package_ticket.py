import pytest

from tests.fakes import edit_file, finish, read_file
from tests.support.scenario import make_context
from veil.engine import run

REQUIREMENTS = "flask==1.0.0\nrequests==2.0.0\n"
PACKAGE_JSON = '{\n  "dependencies": {"lodash": "4.17.15"}\n}\n'
LOCKFILE = '{"LOCKED-9f3a": "lodash 4.17.15"}\n'
LOCKFILE_NAMES = ["package-lock.json", "web/yarn.lock"]


def package_fields(**changes):
    fields = {
        "file": "requirements.txt",
        "line": None,
        "package": "flask",
        "installed_version": "1.0.0",
        "fixed_version": "1.0.4",
    }
    return {**fields, **changes}


def fix_package(tmp_path, script, files, **fields):
    context, tracker, repos, model = make_context(
        tmp_path, script, files=files, **package_fields(**fields)
    )
    report = run(context)
    return report, tracker, repos, model


def test_a_package_ticket_edits_the_manifest_and_the_pr_names_the_package(tmp_path):
    report, tracker, repos, _ = fix_package(
        tmp_path,
        [
            [edit_file("requirements.txt", "flask==1.0.0", "flask==1.0.4")],
            [finish("Short explanation.")],
        ],
        {"requirements.txt": REQUIREMENTS},
    )

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert "flask==1.0.4" in repos.file_on(pr, "requirements.txt")
    assert "## GR-100 · package `flask` in `requirements.txt`" in pr.body
    assert "lockfile is not regenerated" in pr.body
    assert "None" not in pr.body
    assert tracker.labels_on("GR-100") == []


def test_the_model_gets_the_package_and_both_versions(tmp_path):
    _, _, _, model = fix_package(
        tmp_path,
        [
            [edit_file("requirements.txt", "flask==1.0.0", "flask==1.0.4")],
            [finish("Short explanation.")],
        ],
        {"requirements.txt": REQUIREMENTS},
        fixed_version="1.0.4, 2.0.1",
    )

    first = model.received[0][1]["content"]
    assert "flask" in first and "1.0.0" in first and "1.0.4, 2.0.1" in first
    assert "Line:" not in first


@pytest.mark.parametrize("lockfile", LOCKFILE_NAMES)
def test_a_package_ticket_on_a_lockfile_edits_the_manifest_and_never_reads_the_lockfile(
    tmp_path, lockfile
):
    folder = lockfile.rpartition("/")[0]
    manifest = f"{folder}/package.json" if folder else "package.json"
    report, _, repos, model = fix_package(
        tmp_path,
        [
            [read_file(lockfile)],
            [edit_file(manifest, '"4.17.15"', '"4.17.21"')],
            [finish("Short explanation.")],
        ],
        {manifest: PACKAGE_JSON, lockfile: LOCKFILE},
        file=lockfile,
        package="lodash",
        installed_version="4.17.15",
        fixed_version="4.17.21",
    )

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert repos.changed_paths_on(pr) == {manifest}
    assert "LOCKED-9f3a" not in model.everything_received()
    assert f"in `{manifest}`" in pr.body


@pytest.mark.parametrize(
    ("installed", "fixed", "flagged"),
    [
        ("1.2.0", "2.0.1", True),
        ("1.2.0", "2.0.1, 3.0.0", True),
        ("1.2.0", "1.2.5, 2.0.1", False),
        ("1.2.0", "1.2.5", False),
        ("1.2.0", None, False),
    ],
    ids=["major", "all-major", "same-major-fix-exists", "patch", "no-fix"],
)
def test_a_major_jump_between_the_ticket_versions_flags_the_fix(
    tmp_path, installed, fixed, flagged
):
    report, tracker, repos, _ = fix_package(
        tmp_path,
        [
            [edit_file("requirements.txt", "flask==1.0.0", "flask>=1.0.1")],
            [finish("Short explanation.")],
        ],
        {"requirements.txt": REQUIREMENTS},
        installed_version=installed,
        fixed_version=fixed,
    )

    [pr] = repos.pull_requests
    if flagged:
        reason = (
            f"The dependency `flask` in requirements.txt goes from {installed} "
            f"to {fixed.split(', ')[0]}. "
            "A version change of this size can break the code that uses it."
        )
        assert tracker.labels_on("GR-100") == ["breaking-change"]
        assert f"**Breaking change**\n{reason}\n\n" in pr.body
        assert report.breaking["GR-100"] == reason
    else:
        assert tracker.labels_on("GR-100") == []
        assert report.breaking == {}


def test_a_major_bump_in_the_manifest_is_one_reason_not_two(tmp_path):
    report, _, _, _ = fix_package(
        tmp_path,
        [
            [edit_file("requirements.txt", "flask==1.0.0", "flask==2.0.1")],
            [finish("Short explanation.")],
        ],
        {"requirements.txt": REQUIREMENTS},
        installed_version="1.0.0",
        fixed_version="2.0.1",
    )

    assert report.breaking["GR-100"].count("The dependency `flask`") == 1
