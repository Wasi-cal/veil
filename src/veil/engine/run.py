from veil.engine.constants.names import STOPPED_TOKEN_EXPIRED
from veil.engine.context import Context
from veil.engine.eligibility.select import distinct, select_eligible
from veil.engine.errors.token_expired import TokenExpired
from veil.engine.fix.group import fix_group
from veil.engine.fix.left_over import leave_for_next_run
from veil.engine.grouping.plan import plan_groups
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket


def run(context: Context) -> RunReport:
    """Fix the eligible Gozu Tickets. Return the report of the run.

    The Engine skips a ticket that has a fix already. It puts the rest into groups. Each group gets one Fix PR.
    Each ticket has its own token cap. A ticket that uses its cap becomes a Failed Fix, and the run goes on.
    If GitHub refuses the token, the run stops. It cannot publish. It leaves the rest for the next run and reports why.
    """
    report = RunReport()
    tickets = distinct(context.tracker.open_tickets())
    try:
        _fix(context, tickets, report)
    except TokenExpired:
        _leave_unhandled(tickets, report)
        report.stopped = STOPPED_TOKEN_EXPIRED
    return report.redacted(context.redact)


def _fix(context: Context, tickets: list[Ticket], report: RunReport) -> None:
    eligible = select_eligible(tickets, context.repo_provider, context.settings, report)
    for group in plan_groups(eligible, context.settings):
        fix_group(context, group, report)


def _leave_unhandled(tickets: list[Ticket], report: RunReport) -> None:
    """Leave each ticket without an outcome for the next run."""
    leave_for_next_run([t for t in tickets if t.key not in report.outcomes], report)
