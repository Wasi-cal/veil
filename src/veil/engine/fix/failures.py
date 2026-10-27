from veil.engine.constants.outcomes import FAILED
from veil.engine.context import Context
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket

FAILED_FIX_LABEL = "veil-failed-fix"


def record_failed_fix(
    context: Context, ticket: Ticket, failed: FailedFix, report: RunReport
) -> None:
    """Leave the ticket open with a reason comment and the marker label."""
    context.tracker.add_comment(ticket.key, f"Failed Fix. {failed.reason}")
    context.tracker.add_label(ticket.key, FAILED_FIX_LABEL)
    report.outcomes[ticket.key] = FAILED
