from veil.engine.constants.outcomes import FAILED
from veil.engine.context import Context
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket


def record_failed_fix(
    context: Context, ticket: Ticket, failed: FailedFix, report: RunReport
) -> None:
    """Leave the ticket open with the marker label and a reason comment.

    The label comes first. If the comment fails, the next run still skips the ticket and writes no second comment.
    """
    context.tracker.add_label(ticket.key, context.settings.failed_fix_label)
    context.tracker.add_comment(
        ticket.key, context.redact(f"Failed Fix. {failed.reason}")
    )
    report.outcomes[ticket.key] = FAILED
