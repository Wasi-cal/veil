from tests.engine.support import GOOD_EDIT, VULNERABLE, make_context
from tests.fakes import finish, list_dir, read_file, search
from veil.engine import run

NUMBERED = "".join(f"L{n:04d}\n" for n in range(1, 1001))


def results_for(tmp_path, calls, files):
    """Run one Fix attempt. Return the result that the model gets for each call in `calls`."""
    script = [[call] for call in calls] + [[GOOD_EDIT], [finish("Fixed.")]]
    context, _, _, model = make_context(
        tmp_path, script, files={"app.py": VULNERABLE, **files}
    )
    run(context)
    return [model.received[i + 1][-1]["content"] for i in range(len(calls))]


def test_read_file_returns_at_most_300_lines_and_a_note_to_narrow(tmp_path):
    [first, later] = results_for(
        tmp_path,
        [read_file("big.txt"), read_file("big.txt", start_line=301)],
        {"big.txt": NUMBERED},
    )

    assert "L0300" in first
    assert "L0301" not in first
    assert "narrow" in first.lower()
    assert "L0301" in later
    assert "L0600" in later
    assert "L0601" not in later


def test_search_returns_at_most_50_matches_and_a_note_to_narrow(tmp_path):
    [result] = results_for(
        tmp_path,
        [search("L0")],
        {"big.txt": NUMBERED},
    )

    match_lines = [line for line in result.splitlines() if line.startswith("big.txt:")]
    assert len(match_lines) == 50
    assert "narrow" in result.lower()


def test_every_tool_result_is_capped_at_8_kb(tmp_path):
    wide = "".join(f"{n:03d} " + "x" * 196 + "\n" for n in range(100))
    results = results_for(
        tmp_path,
        [read_file("wide.txt"), search("x"), list_dir(".")],
        {"wide.txt": wide},
    )

    for result in results:
        assert len(result.encode()) <= 8 * 1024
    assert "narrow" in results[0].lower()


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
