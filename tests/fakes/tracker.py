from veil.engine import Ticket


def make_ticket(
    key: str = "GR-100",
    repo: str = "acme/app",
    file: str = "app.py",
    line: int = 1,
    severity: str = "Medium",
    finding: str = "Avoid eval on user input.",
) -> Ticket:
    return Ticket(
        key=key, repo=repo, file=file, line=line, severity=severity, finding=finding
    )


class FakeTracker:
    def __init__(self, tickets: list[Ticket]):
        self._tickets = tickets
        self._status: dict[str, str] = {t.key: "To Do" for t in tickets}
        self._comments: dict[str, list[str]] = {t.key: [] for t in tickets}
        self._labels: dict[str, list[str]] = {t.key: [] for t in tickets}

    def open_tickets(self) -> list[Ticket]:
        return list(self._tickets)

    def add_comment(self, key: str, text: str) -> None:
        self._comments[key].append(text)

    def set_status(self, key: str, status: str) -> None:
        self._status[key] = status

    def add_label(self, key: str, label: str) -> None:
        self._labels[key].append(label)

    def labels_on(self, key: str) -> list[str]:
        return list(self._labels[key])

    def status_of(self, key: str) -> str:
        return self._status[key]

    def comments_on(self, key: str) -> list[str]:
        return list(self._comments[key])
