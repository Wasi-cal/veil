import posixpath

from veil.engine.constants.names import BUCKET_RANK
from veil.engine.grouping.severity import bucket_of
from veil.engine.models.config.settings import Settings
from veil.engine.models.group.fix_group import FixGroup
from veil.engine.models.ticket.ticket import Ticket


def plan_groups(tickets: list[Ticket], settings: Settings) -> list[FixGroup]:
    """Put the tickets into groups. One group is one Fix PR. High groups come first, then Medium, then Low.

    Tickets that flag the same file in the same Source PR share one group, because their Fixes overlap.
    Each other ticket gets its own group. There is no cap on the number of groups.
    A group takes the rank of its highest ticket. Groups of equal rank keep the order of the tickets.
    """
    by_file: dict[tuple[str, str, str], list[Ticket]] = {}
    for ticket in tickets:
        file = posixpath.normpath(ticket.file.replace("\\", "/"))
        by_file.setdefault((ticket.repo, ticket.branch, file), []).append(ticket)
    groups = [
        FixGroup(
            repo=repo,
            branch=branch,
            tickets=tuple(group),
            reason=(
                f"These Fixes are in one PR because they change the same file: {file}."
                if len(group) > 1
                else None
            ),
        )
        for (repo, branch, file), group in by_file.items()
    ]
    return sorted(groups, key=lambda group: _rank(group, settings))


def _rank(group: FixGroup, settings: Settings) -> int:
    return min(
        BUCKET_RANK[bucket_of(ticket.severity, settings.severity_map)]
        for ticket in group.tickets
    )
