import difflib

from veil.engine.failed_fix import FailedFix
from veil.engine.interfaces import Workspace
from veil.engine.models.settings import Settings
from veil.engine.path_rules import RuleViolation, check_editable
from veil.engine.syntax import check_parses


class EditRejected(Exception):
    """An edit broke a limit or a rule. The message goes back to the model."""


class WorkingCopy:
    """Applies edits to a Workspace. Every check runs before anything is written."""

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
            raise EditRejected(f"Edit rejected: {violation}") from None
        try:
            current = self.read(path)
        except (FileNotFoundError, IsADirectoryError):
            raise EditRejected("Edit rejected: new files are not allowed.") from None
        if old not in current:
            raise EditRejected("Edit rejected: the text to replace was not found.")
        updated = current.replace(old, new, 1)
        if current and not updated:
            raise EditRejected("Edit rejected: deleting a file is not allowed.")
        originals = {**self._originals, path: self._originals.get(path, current)}
        currents = {**self._current, path: updated}
        if _changed_lines(originals, currents) > self._settings.diff_limit:
            raise EditRejected(
                f"Edit rejected: it would cross the diff limit of {self._settings.diff_limit} changed lines."
            )
        self._workspace.write_file(path, updated)
        self._originals, self._current = originals, currents

    def verify(self) -> None:
        """Checks at `finish`. Raise FailedFix if the change is empty, too big or broken."""
        changed = _changed_lines(self._originals, self._current)
        if changed == 0:
            raise FailedFix("The model finished without making any change.")
        if changed > self._settings.diff_limit:
            raise FailedFix(
                f"The change crosses the diff limit of {self._settings.diff_limit} lines."
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
