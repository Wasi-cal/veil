from veil.engine.constants.outcomes import FAILED, FIXED
from veil.engine.constants.statuses import IN_REVIEW
from veil.engine.constants.tools import FINISH
from veil.engine.context import Context
from veil.engine.failed_fix import FailedFix
from veil.engine.models.run_report import RunReport
from veil.engine.models.ticket import Ticket
from veil.engine.path_rules import RuleViolation, check_readable
from veil.engine.prompt import first_prompt
from veil.engine.toolbox import Toolbox
from veil.engine.working_copy import WorkingCopy

FIX_BRANCH_PREFIX = "gozu/fix-"
FAILED_FIX_LABEL = "veil-failed-fix"


def run(context: Context) -> RunReport:
    report = RunReport()
    for ticket in context.tracker.open_tickets():
        try:
            _fix(context, ticket, report)
        except FailedFix as failed:
            _record_failed_fix(context, ticket, failed, report)
    return report


def _fix(context: Context, ticket: Ticket, report: RunReport) -> None:
    settings = context.settings
    workspace = context.repo_provider.open_workspace(ticket.repo)
    working_copy = WorkingCopy(workspace, settings)
    try:
        path = check_readable(ticket.file, settings.extra_refused_read_patterns)
        source = working_copy.read(path)
    except RuleViolation as violation:
        raise FailedFix(f"{ticket.file} cannot be read: {violation}") from None
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        raise FailedFix(f"{ticket.file} is not a text file in {ticket.repo}.") from None
    messages = [{"role": "user", "content": first_prompt(ticket, source)}]
    toolbox = Toolbox(working_copy, settings)
    steps = 0
    finished = False
    while not finished:
        reply = context.model_client.next(messages)
        report.tokens_used += reply.tokens
        steps += 0 if reply.tool_calls else 1  # an empty reply still costs a step
        for call in reply.tool_calls:
            steps += 1
            if call.name == FINISH:
                finished = True
                break
            messages.append({"role": "tool", "content": toolbox.run(call)})
            if steps >= settings.step_cap:
                raise _step_cap_reached(settings.step_cap)
        if not finished and steps >= settings.step_cap:
            raise _step_cap_reached(settings.step_cap)
    working_copy.verify()
    branch = f"{FIX_BRANCH_PREFIX}{ticket.key.lower()}"
    workspace.commit(branch, f"Fix {ticket.key}")
    pr_url = context.repo_provider.open_draft_pr(
        ticket.repo, branch, f"Fix {ticket.key}", ""
    )
    context.tracker.add_comment(ticket.key, f"Draft Fix PR: {pr_url}")
    context.tracker.set_status(ticket.key, IN_REVIEW)
    report.pull_requests.append(pr_url)
    report.outcomes[ticket.key] = FIXED


def _step_cap_reached(cap: int) -> FailedFix:
    return FailedFix(f"Step cap reached: {cap} tool calls without finishing.")


def _record_failed_fix(
    context: Context, ticket: Ticket, failed: FailedFix, report: RunReport
) -> None:
    context.tracker.add_comment(ticket.key, f"Failed Fix: {failed.reason}")
    context.tracker.add_label(ticket.key, FAILED_FIX_LABEL)
    report.outcomes[ticket.key] = FAILED
