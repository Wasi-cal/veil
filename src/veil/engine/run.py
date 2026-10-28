from veil.engine.context import Context
from veil.engine.eligibility.select import distinct, record_skip, skip_reason
from veil.engine.errors.budget_exhausted import BudgetExhausted
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.fix.escalation import fix_ticket
from veil.engine.fix.failures import leave_for_next_run, record_failed_fix
from veil.engine.models.report.run_report import RunReport


def run(context: Context) -> RunReport:
    """Fix the eligible Gozu Tickets. Return the report of the run.

    The Engine checks each ticket just before its attempt. It skips a ticket that has a fix already.
    At the token ceiling the run stops. The current ticket and the rest stay untouched for the next run.
    """
    report = RunReport()
    tickets = distinct(context.tracker.open_tickets())
    for index, ticket in enumerate(tickets):
        reason = skip_reason(ticket, context.repo_provider)
        if reason is not None:
            record_skip(ticket, reason, report)
            continue
        try:
            fix_ticket(context, ticket, report)
        except FailedFix as failed:
            record_failed_fix(context, ticket, failed, report)
        except BudgetExhausted:
            leave_for_next_run(tickets[index:], report)
            break
    return report
