from typing import Literal

from pydantic import BaseModel, ConfigDict


class ExistingFix(BaseModel):
    """A Fix that the repo provider already has for a Gozu Ticket.

    The kind is `open_pr` or `fix_branch`. The run report uses the kind as the reason to skip the ticket.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["open_pr", "fix_branch"]
    branch: str
