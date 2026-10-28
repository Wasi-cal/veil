from pydantic import BaseModel, ConfigDict

from veil.engine.models.ticket.ticket import Ticket


class Fix(BaseModel):
    """The result of one attempt that passed: the ticket, the commit message and the explanation."""

    model_config = ConfigDict(frozen=True)

    ticket: Ticket
    commit_message: str
    explanation: str
