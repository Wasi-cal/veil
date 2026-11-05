import pytest

from tests.fakes import list_dir, read_file, search
from tests.support.tool_results import results_for
from veil.engine.constants.safety import LOCKFILE_NAMES

LOCK_TEXT = "LOCKED-9f3a"
LOCKFILES = sorted(LOCKFILE_NAMES)


@pytest.mark.parametrize("name", LOCKFILES)
def test_read_file_refuses_a_lockfile_and_gives_nothing_from_it(tmp_path, name):
    [result] = results_for(tmp_path, [read_file(name)], {name: LOCK_TEXT})

    assert result.startswith("Refused")
    assert LOCK_TEXT not in result


@pytest.mark.parametrize("name", ["web/package-lock.json", "WEB/Yarn.LOCK"])
def test_a_lockfile_in_a_folder_or_in_other_case_is_refused(tmp_path, name):
    [result] = results_for(tmp_path, [read_file(name)], {name: LOCK_TEXT})

    assert result.startswith("Refused")
    assert LOCK_TEXT not in result


@pytest.mark.parametrize("name", LOCKFILES)
def test_list_dir_hides_each_lockfile(tmp_path, name):
    [result] = results_for(tmp_path, [list_dir(".")], {name: LOCK_TEXT, "pkg.json": ""})

    assert name not in result.splitlines()
    assert "pkg.json" in result.splitlines()


def test_search_over_the_repository_returns_no_lockfile_line(tmp_path):
    files = {name: f"{LOCK_TEXT} value\n" for name in LOCKFILES}
    files["web/package.json"] = f"{LOCK_TEXT} manifest value\n"

    [result] = results_for(tmp_path, [search(f"{LOCK_TEXT}")], files)

    assert result.splitlines() == [f"web/package.json:1:{LOCK_TEXT} manifest value"]


def test_a_manifest_and_a_normal_file_still_read(tmp_path):
    manifest, normal = results_for(
        tmp_path,
        [read_file("package.json"), read_file("notes.md")],
        {"package.json": '{"name": "app"}\n', "notes.md": "plain\n"},
    )

    assert '"name": "app"' in manifest
    assert "plain" in normal


@pytest.mark.parametrize(
    "name",
    [
        "bun.lock",
        "pdm.lock",
        "podfile.lock",
        "pubspec.lock",
        "flake.lock",
        "deno.lock",
        "packages.lock.json",
        "package.resolved",
        "gradle.lockfile",
        "mix.lock",
    ],
)
def test_the_lockfiles_of_other_package_managers_are_in_the_list(name):
    assert name in LOCKFILE_NAMES
