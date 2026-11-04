from pydantic import BaseModel, ConfigDict

from veil.engine.models.ticket.ticket import Ticket


class Fix(BaseModel):
    """The result of one attempt that passed: the ticket, the commit message and the three parts of the explanation.

    `breaking` is true if the model says the Fix may break something. `breaking_reason` then says why.
    """

    model_config = ConfigDict(frozen=True)

    ticket: Ticket
    commit_message: str
    problem: str
    change: str
    solves: str
    breaking: bool = False
    breaking_reason: str | None = None
