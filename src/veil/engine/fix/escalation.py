from veil.engine.context import Context
from veil.engine.errors.attempt_failed import AttemptFailed
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.fix.attempt import attempt
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket


def fix_ticket(context: Context, ticket: Ticket, report: RunReport) -> None:
    """Try the cheap model. If the attempt fails, try the strong model once on a fresh checkout.

    Raise FailedFix if both attempts fail.
    """
    settings = context.settings
    try:
        attempt(context, ticket, report, settings.cheap_model)
    except AttemptFailed as first:
        try:
            attempt(
                context, ticket, report, settings.strong_model, failure=first.reason
            )
        except AttemptFailed as second:
            raise FailedFix(
                f"The first attempt failed. {first.reason} The second attempt failed. {second.reason}"
            ) from None
