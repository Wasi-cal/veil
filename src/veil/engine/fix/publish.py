from veil.engine.constants.branches import FIX_BRANCH_PREFIX
from veil.engine.constants.outcomes import FIXED
from veil.engine.constants.statuses import IN_REVIEW
from veil.engine.context import Context
from veil.engine.interfaces.workspace import Workspace
from veil.engine.models.provider.draft_pr import DraftPr
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket


def publish(
    context: Context, workspace: Workspace, ticket: Ticket, report: RunReport
) -> None:
    """Commit the Fix, open a draft Fix PR and update the ticket."""
    branch = f"{FIX_BRANCH_PREFIX}{ticket.key.lower()}"
    workspace.commit(branch, f"Fix {ticket.key}")
    labels = (ticket.issue_label,) if ticket.issue_label else ()
    draft = DraftPr(
        repo=ticket.repo,
        head=branch,
        base=ticket.branch,
        title=f"Fix {ticket.key}",
        body="",
        labels=labels,
    )
    pr_url = context.repo_provider.open_draft_pr(draft)
    context.tracker.add_comment(
        ticket.key, f"The Engine opened a draft Fix PR: {pr_url}"
    )
    context.tracker.set_status(ticket.key, IN_REVIEW)
    report.pull_requests.append(pr_url)
    report.outcomes[ticket.key] = FIXED
