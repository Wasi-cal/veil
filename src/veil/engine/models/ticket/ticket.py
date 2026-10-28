from pydantic import BaseModel, ConfigDict

from veil.engine.constants.labels import ISSUE_LABEL_PREFIX


class Ticket(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    repo: str
    file: str
    line: int
    severity: str
    finding: str
    branch: str
    labels: tuple[str, ...]

    @property
    def issue_label(self) -> str | None:
        """The label that names the scan finding, for example issue-3f9a. Gozu sets it on each ticket."""
        return next(
            (label for label in self.labels if label.startswith(ISSUE_LABEL_PREFIX)),
            None,
        )
