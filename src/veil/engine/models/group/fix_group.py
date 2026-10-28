from typing import Literal

from pydantic import BaseModel, ConfigDict

from veil.engine.models.ticket.ticket import Ticket


class FixGroup(BaseModel):
    """The Gozu Tickets that go into one Fix PR. All tickets have the same repository and the same Source PR branch.

    A shared group holds Low and Medium tickets. A high group holds one High ticket, or High tickets that overlap.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["shared", "high"]
    repo: str
    branch: str
    tickets: tuple[Ticket, ...]
    reason: str | None = None
