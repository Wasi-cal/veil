from veil.engine.context import Context
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.errors.rule_violation import RuleViolation
from veil.engine.fix.budget import ensure_budget
from veil.engine.fix.conversation import converse
from veil.engine.fix.prompt import first_prompt
from veil.engine.interfaces.workspace import Workspace
from veil.engine.models.fix.fix import Fix
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket
from veil.engine.tools.handlers.readable import readable_path
from veil.engine.tools.toolbox import Toolbox
from veil.engine.workspace.working_copy import WorkingCopy


def attempt(
    context: Context,
    ticket: Ticket,
    report: RunReport,
    model: str,
    workspace: Workspace,
    failure: str | None = None,
) -> Fix:
    """Try to fix one Gozu Ticket with one model. Return the Fix. The edits stay in the workspace, not committed.

    Raise AttemptFailed if the attempt fails after the model started.
    Raise FailedFix if the Engine cannot read the file of the ticket.
    """
    settings = context.settings
    ensure_budget(report, settings)
    working_copy = WorkingCopy(workspace, settings)
    try:
        source = working_copy.read(readable_path(ticket.file, settings))
    except RuleViolation as violation:
        raise FailedFix(f"The Engine cannot read {ticket.file}. {violation}") from None
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        raise FailedFix(
            f"The file {ticket.file} is not a text file in {ticket.repo}."
        ) from None
    messages = [{"role": "user", "content": first_prompt(ticket, source, failure)}]
    finish = converse(
        context.model_client,
        model,
        Toolbox(working_copy, settings),
        messages,
        settings,
        report,
    )
    working_copy.verify()
    return Fix(
        ticket=ticket,
        commit_message=finish.commit_message,
        explanation=finish.explanation,
    )
