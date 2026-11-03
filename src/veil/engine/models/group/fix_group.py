from pydantic import BaseModel, ConfigDict

from veil.engine.models.ticket.ticket import Ticket


class FixGroup(BaseModel):
    """The Gozu Tickets that go into one Fix PR. All tickets have the same repository, the same Source PR branch and the same file."""

    model_config = ConfigDict(frozen=True)

    repo: str
    branch: str
    tickets: tuple[Ticket, ...]
    reason: str | None = None

    def branch_name(self, first_fixed_key: str, prefix: str) -> str:
        """The branch of the Fix PR. It starts with the prefix and names the first Fix that passed.

        A ticket that failed gives no name. A later run can then make a new PR for that ticket without a branch clash.
        """
        return f"{prefix}{first_fixed_key.lower()}"
