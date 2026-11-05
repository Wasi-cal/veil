import logging

from veil.engine.constants.limits import STRONG_MODEL_ATTEMPT
from veil.engine.context import Context
from veil.engine.errors.attempt_failed import AttemptFailed
from veil.engine.errors.budget_exhausted import BudgetExhausted
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.fix.attempt import attempt
from veil.engine.fix.budget import TicketBudget
from veil.engine.interfaces.workspace import Workspace
from veil.engine.models.fix.fix import Fix
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket

log = logging.getLogger(__name__)


def fix_ticket(
    context: Context, ticket: Ticket, report: RunReport, workspace: Workspace
) -> Fix:
    """Try the cheap model. If the attempt fails, try the strong model once from the last commit.

    A failed attempt discards its edits, so the next attempt starts from clean files.
    With the setting `max_attempts` at 1, the Engine tries the cheap model only.
    The ticket has one token budget for all its attempts. At the cap the Engine stops the work on the ticket.
    Raise FailedFix if every attempt fails or the ticket uses its token cap.
    """
    settings = context.settings
    budget = TicketBudget(settings.ticket_token_cap)
    log.info("%s: start. Model %s.", ticket.key, settings.cheap_model)
    try:
        return _attempts(context, ticket, report, budget, workspace)
    except BudgetExhausted:
        workspace.discard_changes()
        log.warning("%s: token cap of %d reached.", ticket.key, budget.cap)
        raise FailedFix(
            f"The ticket used its token cap of {budget.cap} tokens."
        ) from None
    finally:
        report.usage[ticket.key] = budget.usage
        log.info(
            "%s: tokens input %d, output %d, total %d. Escalated: %s.",
            ticket.key,
            budget.usage.input,
            budget.usage.output,
            budget.usage.total,
            "yes" if budget.usage.escalated else "no",
        )


def _attempts(
    context: Context,
    ticket: Ticket,
    report: RunReport,
    budget: TicketBudget,
    workspace: Workspace,
) -> Fix:
    settings = context.settings
    try:
        return attempt(
            context,
            ticket,
            report,
            budget,
            settings.cheap_model,
            workspace,
            reasoning_effort=settings.cheap_reasoning_effort,
        )
    except AttemptFailed as first:
        workspace.discard_changes()
        log.warning(
            "%s: first attempt failed. %s", ticket.key, context.redact(first.reason)
        )
        if settings.max_attempts < STRONG_MODEL_ATTEMPT:
            raise FailedFix(f"The attempt failed. {first.reason}") from None
        budget.usage.escalated = True
        log.info("%s: escalate to %s.", ticket.key, settings.strong_model)
        try:
            return attempt(
                context,
                ticket,
                report,
                budget,
                settings.strong_model,
                workspace,
                failure=context.redact(first.reason),
            )
        except AttemptFailed as second:
            workspace.discard_changes()
            log.warning(
                "%s: second attempt failed. %s",
                ticket.key,
                context.redact(second.reason),
            )
            raise FailedFix(
                f"The first attempt failed. {first.reason} The second attempt failed. {second.reason}"
            ) from None
