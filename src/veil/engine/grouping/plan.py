import posixpath

from veil.engine.constants.severity import HIGH
from veil.engine.grouping.severity import bucket_of
from veil.engine.models.config.settings import Settings
from veil.engine.models.group.fix_group import FixGroup
from veil.engine.models.group.group_plan import GroupPlan
from veil.engine.models.ticket.ticket import Ticket


def plan_groups(tickets: list[Ticket], settings: Settings) -> GroupPlan:
    """Put the tickets into groups. High groups come first, then the shared groups.

    Low and Medium tickets with the same repository and the same Source PR branch share one group.
    A shared group holds at most `shared_pr_max` tickets. The other tickets wait for a later run.
    High tickets that flag the same file in the same Source PR share one group, because their Fixes overlap.
    Each other High ticket gets its own group.
    """
    high: dict[tuple[str, str, str], list[Ticket]] = {}
    shared: dict[tuple[str, str], list[Ticket]] = {}
    for ticket in tickets:
        if bucket_of(ticket.severity, settings.severity_map) == HIGH:
            file = posixpath.normpath(ticket.file.replace("\\", "/"))
            key = (ticket.repo, ticket.branch, file)
            high.setdefault(key, []).append(ticket)
        else:
            shared.setdefault((ticket.repo, ticket.branch), []).append(ticket)
    high_groups = [
        FixGroup(
            kind="high",
            repo=repo,
            branch=branch,
            tickets=tuple(group),
            reason=(
                f"These Fixes are in one PR because they change the same file: {file}."
                if len(group) > 1
                else None
            ),
        )
        for (repo, branch, file), group in high.items()
    ]
    cap = settings.shared_pr_max
    shared_groups = [
        FixGroup(kind="shared", repo=repo, branch=branch, tickets=tuple(group[:cap]))
        for (repo, branch), group in shared.items()
    ]
    left = tuple(ticket for group in shared.values() for ticket in group[cap:])
    return GroupPlan(groups=(*high_groups, *shared_groups), left_for_next_run=left)
