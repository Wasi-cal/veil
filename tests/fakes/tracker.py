from veil.engine import Ticket


def make_ticket(
    key: str = "GR-100",
    repo: str = "acme/app",
    file: str = "app.py",
    line: int = 1,
    severity: str = "Medium",
    finding: str = "Avoid eval on user input.",
    branch: str = "feature",
    labels: tuple[str, ...] | None = None,
) -> Ticket:
    """Build a ticket. Each key gets its own issue label, so tickets do not share one."""
    return Ticket(
        key=key,
        repo=repo,
        file=file,
        line=line,
        severity=severity,
        finding=finding,
        branch=branch,
        labels=(f"issue-{key.lower()}",) if labels is None else labels,
    )


class FakeTracker:
    def __init__(self, tickets: list[Ticket]):
        self._tickets = tickets
        self._status: dict[str, str] = {t.key: "To Do" for t in tickets}
        self._comments: dict[str, list[str]] = {t.key: [] for t in tickets}
        self._labels: dict[str, list[str]] = {t.key: [] for t in tickets}
        self._explode_on_next_comment = False

    def explode_on_next_comment(self) -> None:
        """Make the next add_comment raise once, as a tracker that is down."""
        self._explode_on_next_comment = True

    def open_tickets(self) -> list[Ticket]:
        """Return the tickets with the labels that the Engine added, as a real tracker does."""
        return [
            t.model_copy(update={"labels": (*t.labels, *self._labels[t.key])})
            for t in self._tickets
        ]

    def add_comment(self, key: str, text: str) -> None:
        if self._explode_on_next_comment:
            self._explode_on_next_comment = False
            raise RuntimeError("The tracker is down.")
        self._comments[key].append(text)

    def set_status(self, key: str, status: str) -> None:
        self._status[key] = status

    def add_label(self, key: str, label: str) -> None:
        self._labels[key].append(label)

    def remove_label(self, key: str, label: str) -> None:
        """A person deletes a label in the tracker."""
        self._labels[key].remove(label)

    def labels_on(self, key: str) -> list[str]:
        return list(self._labels[key])

    def status_of(self, key: str) -> str:
        return self._status[key]

    def comments_on(self, key: str) -> list[str]:
        return list(self._comments[key])
