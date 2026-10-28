from pydantic import BaseModel, ConfigDict

from veil.engine.models.group.fix_group import FixGroup
from veil.engine.models.ticket.ticket import Ticket


class GroupPlan(BaseModel):
    """The groups that the Engine fixes in this run, and the tickets that wait for a later run."""

    model_config = ConfigDict(frozen=True)

    groups: tuple[FixGroup, ...]
    left_for_next_run: tuple[Ticket, ...]
