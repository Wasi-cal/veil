from veil.engine.constants.outcomes import FIXED
from veil.engine.constants.statuses import IN_REVIEW
from veil.engine.constants.tools import EDIT_FILE, FINISH
from veil.engine.context import Context
from veil.engine.models.run_report import RunReport
from veil.engine.models.ticket import Ticket
from veil.engine.prompt import first_prompt

FIX_BRANCH_PREFIX = "gozu/fix-"


def run(context: Context) -> RunReport:
    report = RunReport()
    for ticket in context.tracker.open_tickets():
        _fix(context, ticket, report)
    return report


def _fix(context: Context, ticket: Ticket, report: RunReport) -> None:
    workspace = context.repo_provider.open_workspace(ticket.repo)
    prompt = first_prompt(ticket, workspace.read_file(ticket.file))
    messages = [{"role": "user", "content": prompt}]
    finished = False
    while not finished:
        reply = context.model_client.next(messages)
        report.tokens_used += reply.tokens
        for call in reply.tool_calls:
            if call.name == EDIT_FILE:
                workspace.edit_file(**call.arguments)
            elif call.name == FINISH:
                finished = True
    branch = f"{FIX_BRANCH_PREFIX}{ticket.key.lower()}"
    workspace.commit(branch, f"Fix {ticket.key}")
    pr_url = context.repo_provider.open_draft_pr(
        ticket.repo, branch, f"Fix {ticket.key}", ""
    )
    context.tracker.add_comment(ticket.key, f"Draft Fix PR: {pr_url}")
    context.tracker.set_status(ticket.key, IN_REVIEW)
    report.pull_requests.append(pr_url)
    report.outcomes[ticket.key] = FIXED
