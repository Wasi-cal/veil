from pydantic import BaseModel, ConfigDict

from veil.engine.models.ticket.ticket import Ticket


class Fix(BaseModel):
    """The result of one attempt that passed: the ticket, the commit message and the three parts of the explanation.

    `breaking` is true if the model or an Engine check says the Fix may break something.
    `breaking_reasons` says why: the reason of the model first, then the reasons of the checks.
    """

    model_config = ConfigDict(frozen=True)

    ticket: Ticket
    commit_message: str
    problem: str
    change: str
    solves: str
    breaking: bool = False
    breaking_reasons: tuple[str, ...] = ()
