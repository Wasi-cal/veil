from pydantic import BaseModel, ConfigDict

from veil.engine.constants.names import ISSUE_LABEL_PREFIX


class Ticket(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    repo: str
    file: str
    line: int | None = None
    severity: str
    finding: str
    branch: str
    labels: tuple[str, ...]
    package: str | None = None
    installed_version: str | None = None
    fixed_version: str | None = None

    @property
    def issue_label(self) -> str | None:
        """The label that names the scan finding, for example issue-3f9a. Gozu sets it on each ticket."""
        return next(
            (label for label in self.labels if label.startswith(ISSUE_LABEL_PREFIX)),
            None,
        )
