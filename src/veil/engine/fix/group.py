from veil.engine.context import Context
from veil.engine.errors.budget_exhausted import BudgetExhausted
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.fix.budget import ensure_budget
from veil.engine.fix.escalation import fix_ticket
from veil.engine.fix.failures import record_failed_fix
from veil.engine.fix.publish import publish
from veil.engine.models.fix.fix import Fix
from veil.engine.models.group.fix_group import FixGroup
from veil.engine.models.report.run_report import RunReport


def fix_group(context: Context, group: FixGroup, report: RunReport) -> None:
    """Fix the tickets of a group in one checkout. Commit each Fix. Then open one draft Fix PR.

    A ticket that ends as a Failed Fix stays out of the PR.
    At the token ceiling the Engine still publishes the Fixes that passed. Then it raises BudgetExhausted.
    """
    ensure_budget(report, context.settings)
    workspace = context.repo_provider.open_workspace(group.repo, group.branch)
    fixes: list[Fix] = []
    branch: str | None = None
    budget_error: BudgetExhausted | None = None
    try:
        for ticket in group.tickets:
            try:
                fix = fix_ticket(context, ticket, report, workspace)
            except FailedFix as failed:
                record_failed_fix(context, ticket, failed, report)
                continue
            if branch is None:
                branch = group.branch_name(
                    fix.ticket.key, context.settings.branch_prefix
                )
            workspace.commit(branch, context.redact(fix.commit_message))
            fixes.append(fix)
    except BudgetExhausted as exhausted:
        workspace.discard_changes()
        budget_error = exhausted
    if branch is not None:
        publish(context, group, fixes, branch, report)
    if budget_error is not None:
        raise budget_error
