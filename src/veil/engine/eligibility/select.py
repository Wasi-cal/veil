from veil.engine.constants.labels import FAILED_FIX_LABEL
from veil.engine.constants.outcomes import SKIPPED
from veil.engine.constants.skip_reasons import (
    DUPLICATE_ISSUE,
    FAILED_FIX,
    NO_ISSUE_LABEL,
    RAISED_AGAINST_FIX_BRANCH,
    SOURCE_PR_NOT_OPEN,
)
from veil.engine.interfaces.repo_provider import RepoProvider
from veil.engine.models.config.settings import Settings
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


def select_eligible(
    tickets: list[Ticket],
    repo_provider: RepoProvider,
    settings: Settings,
    report: RunReport,
) -> list[Ticket]:
    """Return the tickets that the Engine may fix. Put each other ticket in the report with its reason.

    Two tickets with the same issue label in one repository are one finding. The Engine keeps the first.
    """
    eligible: list[Ticket] = []
    issues_in_this_run: set[tuple[str, str]] = set()
    for ticket in tickets:
        reason = _skip_reason(ticket, repo_provider, settings, issues_in_this_run)
        if reason is None:
            eligible.append(ticket)
            issues_in_this_run.add((ticket.repo, ticket.issue_label or ""))
        else:
            report.outcomes[ticket.key] = SKIPPED
            report.skipped.setdefault(reason, []).append(ticket.key)
    return eligible


def _skip_reason(
    ticket: Ticket,
    repo_provider: RepoProvider,
    settings: Settings,
    issues_in_this_run: set[tuple[str, str]],
) -> str | None:
    """Return why the Engine must not fix this ticket, or None if it may. Cheap rules come first."""
    if ticket.branch.startswith(settings.branch_prefix):
        return RAISED_AGAINST_FIX_BRANCH
    if FAILED_FIX_LABEL in ticket.labels:
        return FAILED_FIX
    if ticket.issue_label is None:
        return NO_ISSUE_LABEL
    if (ticket.repo, ticket.issue_label) in issues_in_this_run:
        return DUPLICATE_ISSUE
    if not repo_provider.has_open_pr(ticket.repo, ticket.branch):
        return SOURCE_PR_NOT_OPEN
    existing = repo_provider.find_existing_fix(ticket.repo, ticket.issue_label)
    return None if existing is None else existing.kind
