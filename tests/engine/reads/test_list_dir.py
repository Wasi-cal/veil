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
