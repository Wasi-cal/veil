from veil.engine.errors.attempt_failed import AttemptFailed
from veil.engine.errors.edit_rejected import EditRejected
from veil.engine.errors.rule_violation import RuleViolation
from veil.engine.interfaces.workspace import Workspace
from veil.engine.models.config.settings import Settings
from veil.engine.workspace.diff import changed_lines
from veil.engine.workspace.path_rules import check_editable
from veil.engine.workspace.syntax import check_parses


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
        if current.strip() and not updated.strip():
            raise EditRejected(
                "Refused: The edit deletes the file. Deletions are not allowed."
            )
        originals = {**self._originals, path: self._originals.get(path, current)}
        currents = {**self._current, path: updated}
        if changed_lines(originals, currents) > self._settings.diff_limit:
            raise EditRejected(
                f"Refused: The edit crosses the diff limit of {self._settings.diff_limit} changed lines."
            )
        self._workspace.write_file(path, updated)
        self._originals, self._current = originals, currents

    def edits(self) -> list[tuple[str, str]]:
        """The old text and the new text of each file that this attempt edited."""
        return [
            (before, self._current[path]) for path, before in self._originals.items()
        ]

    def verify(self) -> None:
        """Run the checks at `finish`. Raise AttemptFailed if the change is empty, too large or does not parse."""
        changed = changed_lines(self._originals, self._current)
        if changed == 0:
            raise AttemptFailed("The model finished and made no change.")
        if changed > self._settings.diff_limit:
            raise AttemptFailed(
                f"The change has more than {self._settings.diff_limit} changed lines. This crosses the diff limit."
            )
        check_parses(self._current)
