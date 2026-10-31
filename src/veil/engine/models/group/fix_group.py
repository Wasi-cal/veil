from pydantic import BaseModel, ConfigDict

from veil.engine.constants.group_kinds import HIGH_GROUP, GroupKind
from veil.engine.models.ticket.ticket import Ticket


class FixGroup(BaseModel):
    """The Gozu Tickets that go into one Fix PR. All tickets have the same repository and the same Source PR branch.

    A shared group holds Low and Medium tickets. A high group holds one High ticket, or High tickets that overlap.
    """

    model_config = ConfigDict(frozen=True)

    kind: GroupKind
    repo: str
    branch: str
    tickets: tuple[Ticket, ...]
    reason: str | None = None

    def branch_name(self, first_fixed_key: str, prefix: str) -> str:
        """The branch of the Fix PR. It starts with the prefix and names the first Fix that passed.

        A ticket that failed gives no name. A later run can then make a new PR for that ticket without a branch clash.
        """
        key = first_fixed_key.lower()
        return f"{prefix}{key}" if self.kind == HIGH_GROUP else f"{prefix}shared-{key}"

    def title(self, keys: list[str]) -> str:
        """The title of the Fix PR. A high group names its tickets. A shared group gives the count."""
        if self.kind == HIGH_GROUP:
            return f"Fix {', '.join(keys)}"
        return f"Fix {len(keys)} ticket{'' if len(keys) == 1 else 's'}"
