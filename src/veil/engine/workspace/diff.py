import difflib


def changed_lines(originals: dict[str, str], currents: dict[str, str]) -> int:
    """Count the changed lines in all edited files."""
    return sum(
        _file_changed_lines(originals[path], currents[path]) for path in originals
    )


def _file_changed_lines(before: str, after: str) -> int:
    """Count each changed line once. A change to a line ending or to a space counts as a change."""
    matcher = difflib.SequenceMatcher(
        None,
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        autojunk=False,
    )
    return sum(
        max(old_end - old_start, new_end - new_start)
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes()
        if tag != "equal"
    )
