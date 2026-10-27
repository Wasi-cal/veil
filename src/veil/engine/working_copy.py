import difflib

from veil.engine.failed_fix import FailedFix
from veil.engine.interfaces import Workspace
from veil.engine.models.settings import Settings
from veil.engine.path_rules import RuleViolation, check_editable
from veil.engine.syntax import check_parses


class EditRejected(Exception):
    """An edit breaks a limit or a rule. The model gets the message."""


class WorkingCopy:
    """Apply edits to a Workspace. Each check runs before the Engine writes anything."""

    def __init__(self, workspace: Workspace, settings: Settings):
        self._workspace = workspace
        self._settings = settings
        self._originals: dict[str, str] = {}
        self._current: dict[str, str] = {}

    def read(self, path: str) -> str:
        if path in self._current:
            return self._current[path]
        return self._workspace.read_file(path)

    def list_files(self) -> list[str]:
        return self._workspace.list_files()

    def edit(self, path: str, old: str, new: str) -> None:
        try:
            path = check_editable(path, self._settings.extra_refused_read_patterns)
        except RuleViolation as violation:
            raise EditRejected(f"Refused: {violation}") from None
        try:
            current = self.read(path)
        except (FileNotFoundError, IsADirectoryError):
            raise EditRejected(
                "Refused: The path is not a file in the repository. New files are not allowed."
            ) from None
        if old not in current:
            raise EditRejected("Refused: The text to replace is not in the file.")
        updated = current.replace(old, new, 1)
        if current and not updated:
            raise EditRejected(
                "Refused: The edit deletes the file. Deletions are not allowed."
            )
        originals = {**self._originals, path: self._originals.get(path, current)}
        currents = {**self._current, path: updated}
        if _changed_lines(originals, currents) > self._settings.diff_limit:
            raise EditRejected(
                f"Refused: The edit crosses the diff limit of {self._settings.diff_limit} changed lines."
            )
        self._workspace.write_file(path, updated)
        self._originals, self._current = originals, currents

    def verify(self) -> None:
        """Run the checks at `finish`. Raise FailedFix if the change is empty, too large or does not parse."""
        changed = _changed_lines(self._originals, self._current)
        if changed == 0:
            raise FailedFix("The model finished and made no change.")
        if changed > self._settings.diff_limit:
            raise FailedFix(
                f"The change has more than {self._settings.diff_limit} changed lines. This crosses the diff limit."
            )
        check_parses(self._current)


def _changed_lines(originals: dict[str, str], currents: dict[str, str]) -> int:
    return sum(
        _file_changed_lines(originals[path], currents[path]) for path in originals
    )


def _file_changed_lines(before: str, after: str) -> int:
    diff = difflib.unified_diff(
        before.splitlines(), after.splitlines(), lineterm="", n=0
    )
    return sum(1 for line in list(diff)[2:] if line[:1] in "+-")
