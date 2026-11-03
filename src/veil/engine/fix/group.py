from veil.engine.context import Context
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.fix.escalation import fix_ticket
from veil.engine.fix.failures import record_failed_fix
from veil.engine.fix.pr_text import commit_text
from veil.engine.fix.publish import publish
from veil.engine.models.fix.fix import Fix
from veil.engine.models.group.fix_group import FixGroup
from veil.engine.models.report.run_report import RunReport


def fix_group(context: Context, group: FixGroup, report: RunReport) -> None:
    """Fix the tickets of a group in one checkout. Commit each Fix. Then open one Fix PR.

    A ticket that ends as a Failed Fix stays out of the PR. This includes a ticket that used its token cap.
    """
    workspace = context.repo_provider.open_workspace(group.repo, group.branch)
    fixes: list[Fix] = []
    branch: str | None = None
    for ticket in group.tickets:
        try:
            fix = fix_ticket(context, ticket, report, workspace)
        except FailedFix as failed:
            record_failed_fix(context, ticket, failed, report)
            context.report_progress(report.tokens_used)
            continue
        if branch is None:
            branch = group.branch_name(fix.ticket.key, context.settings.branch_prefix)
        workspace.commit(branch, context.redact(commit_text(fix)))
        fixes.append(fix)
        context.report_progress(report.tokens_used)
    if branch is not None:
        publish(context, group, fixes, branch, report)
