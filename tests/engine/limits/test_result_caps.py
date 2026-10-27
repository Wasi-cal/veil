from tests.fakes import list_dir, read_file, search
from tests.support.tool_results import results_for

NUMBERED = "".join(f"L{n:04d}\n" for n in range(1, 1001))


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
