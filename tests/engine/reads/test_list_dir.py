from tests.fakes import list_dir
from tests.support.tool_results import results_for


def test_list_dir_lists_only_the_asked_directory_and_hides_secret_files(tmp_path):
    [result] = results_for(
        tmp_path,
        [list_dir("src")],
        {"src/a.py": "", "src/.env": "", "src/deep/b.py": "", "other/c.py": ""},
    )

    names = result.splitlines()
    assert "a.py" in names
    assert "deep/" in names
    assert ".env" not in names
    assert "c.py" not in result


def test_list_dir_hides_the_github_folder_and_everything_in_it(tmp_path):
    root, inside = results_for(
        tmp_path,
        [list_dir("."), list_dir(".github")],
        {"a.py": "", ".github/workflows/ci.yml": "", ".github/CODEOWNERS": ""},
    )

    assert ".github" not in root
    assert "a.py" in root.splitlines()
    assert "ci.yml" not in inside
    assert "CODEOWNERS" not in inside
