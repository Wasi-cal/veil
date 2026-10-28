from typing import Protocol, runtime_checkable

from veil.engine.models.ticket.ticket import Ticket


@runtime_checkable
class Tracker(Protocol):
    def open_tickets(self) -> list[Ticket]:
        """Return the candidate tickets: open, not assigned and with the Gozu label.

        Each ticket carries its Source PR branch and all its labels.
        The labels show the Failed Fix label, so the next run skips that ticket.
        """
        ...

    def add_comment(self, key: str, text: str) -> None: ...
    def set_status(self, key: str, status: str) -> None: ...
    def add_label(self, key: str, label: str) -> None: ...
