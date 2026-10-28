from veil.engine.constants.labels import FAILED_FIX_LABEL
from veil.engine.constants.outcomes import FAILED, LEFT_FOR_NEXT_RUN
from veil.engine.context import Context
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket


def record_failed_fix(
    context: Context, ticket: Ticket, failed: FailedFix, report: RunReport
) -> None:
    """Leave the ticket open with a reason comment and the marker label."""
    context.tracker.add_comment(
        ticket.key, context.redact(f"Failed Fix. {failed.reason}")
    )
    context.tracker.add_label(ticket.key, FAILED_FIX_LABEL)
    report.outcomes[ticket.key] = FAILED


def leave_for_next_run(tickets: list[Ticket], report: RunReport) -> None:
    """Mark these tickets as left for the next run. Do not touch them in the tracker."""
    for ticket in tickets:
        report.outcomes[ticket.key] = LEFT_FOR_NEXT_RUN
