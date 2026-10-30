from veil.engine.interfaces.tracker import Tracker
from veil.engine.models.ticket.ticket import Ticket


class RepoScopedTracker:
    """A tracker that shows the Engine only the tickets of one repo. Each run works on one repo only.

    The GitHub token of a run covers one repo. A ticket of another repo must never reach the Engine.
    """

    def __init__(self, inner: Tracker, repo: str) -> None:
        self._inner = inner
        self._repo = repo

    def open_tickets(self) -> list[Ticket]:
        return [t for t in self._inner.open_tickets() if t.repo == self._repo]

    def add_comment(self, key: str, text: str) -> None:
        self._inner.add_comment(key, text)

    def set_status(self, key: str, status: str) -> None:
        self._inner.set_status(key, status)

    def add_label(self, key: str, label: str) -> None:
        self._inner.add_label(key, label)
