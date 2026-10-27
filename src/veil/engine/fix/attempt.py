from veil.engine.context import Context
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.errors.rule_violation import RuleViolation
from veil.engine.fix.conversation import converse
from veil.engine.fix.prompt import first_prompt
from veil.engine.fix.publish import publish
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket
from veil.engine.tools.handlers.readable import readable_path
from veil.engine.tools.toolbox import Toolbox
from veil.engine.workspace.working_copy import WorkingCopy


def attempt(context: Context, ticket: Ticket, report: RunReport) -> None:
    """Try to fix one Gozu Ticket. Raise FailedFix if the Engine cannot fix it within its limits."""
    settings = context.settings
    workspace = context.repo_provider.open_workspace(ticket.repo)
    working_copy = WorkingCopy(workspace, settings)
    try:
        source = working_copy.read(readable_path(ticket.file, settings))
    except RuleViolation as violation:
        raise FailedFix(f"The Engine cannot read {ticket.file}. {violation}") from None
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        raise FailedFix(
            f"The file {ticket.file} is not a text file in {ticket.repo}."
        ) from None
    messages = [{"role": "user", "content": first_prompt(ticket, source)}]
    converse(
        context.model_client,
        Toolbox(working_copy, settings),
        messages,
        settings,
        report,
    )
    working_copy.verify()
    publish(context, workspace, ticket, report)
