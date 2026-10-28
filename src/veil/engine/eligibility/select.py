from veil.engine.constants.branches import FIX_BRANCH_PREFIX
from veil.engine.constants.labels import FAILED_FIX_LABEL
from veil.engine.constants.outcomes import SKIPPED
from veil.engine.constants.skip_reasons import (
    FAILED_FIX,
    NO_ISSUE_LABEL,
    RAISED_AGAINST_FIX_BRANCH,
    SOURCE_PR_NOT_OPEN,
)
from veil.engine.interfaces.repo_provider import RepoProvider
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket


def distinct(tickets: list[Ticket]) -> list[Ticket]:
    """Keep the first ticket for each key. A tracker can list a ticket twice."""
    seen: set[str] = set()
    unique = []
    for ticket in tickets:
        if ticket.key not in seen:
            seen.add(ticket.key)
            unique.append(ticket)
    return unique


def skip_reason(ticket: Ticket, repo_provider: RepoProvider) -> str | None:
    """Return why the Engine must not fix this ticket now, or None if it may.

    Call this just before the attempt. A PR that the run opened for an earlier ticket then counts.
    """
    if ticket.branch.startswith(FIX_BRANCH_PREFIX):
        return RAISED_AGAINST_FIX_BRANCH
    if FAILED_FIX_LABEL in ticket.labels:
        return FAILED_FIX
    if ticket.issue_label is None:
        return NO_ISSUE_LABEL
    if not repo_provider.has_open_pr(ticket.repo, ticket.branch):
        return SOURCE_PR_NOT_OPEN
    existing = repo_provider.find_existing_fix(ticket.repo, ticket.issue_label)
    return None if existing is None else existing.kind


def record_skip(ticket: Ticket, reason: str, report: RunReport) -> None:
    """Put the ticket in the report as skipped, with its reason."""
    report.outcomes[ticket.key] = SKIPPED
    report.skipped.setdefault(reason, []).append(ticket.key)
