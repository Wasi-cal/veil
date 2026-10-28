from veil.engine.context import Context
from veil.engine.errors.attempt_failed import AttemptFailed
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.fix.attempt import attempt
from veil.engine.interfaces.workspace import Workspace
from veil.engine.models.fix.fix import Fix
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket


def fix_ticket(
    context: Context, ticket: Ticket, report: RunReport, workspace: Workspace
) -> Fix:
    """Try the cheap model. If the attempt fails, try the strong model once from the last commit.

    A failed attempt discards its edits, so the next attempt starts from clean files.
    Raise FailedFix if both attempts fail.
    """
    settings = context.settings
    try:
        return attempt(context, ticket, report, settings.cheap_model, workspace)
    except AttemptFailed as first:
        workspace.discard_changes()
        try:
            return attempt(
                context,
                ticket,
                report,
                settings.strong_model,
                workspace,
                failure=context.redact(first.reason),
            )
        except AttemptFailed as second:
            workspace.discard_changes()
            raise FailedFix(
                f"The first attempt failed. {first.reason} The second attempt failed. {second.reason}"
            ) from None
