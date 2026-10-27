from pydantic import BaseModel, ConfigDict, Field

from veil.engine.interfaces import ModelClient, RepoProvider, Ticket, Tracker
from veil.engine.prompt import first_prompt
from veil.engine.settings import Settings


class Context(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    settings: Settings
    tracker: Tracker
    repo_provider: RepoProvider
    model_client: ModelClient


class RunReport(BaseModel):
    pull_requests: list[str] = Field(default_factory=list)
    outcomes: dict[str, str] = Field(default_factory=dict)
    tokens_used: int = 0


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
            if call.name == "edit_file":
                workspace.edit_file(**call.arguments)
            elif call.name == "finish":
                finished = True
    branch = f"gozu/fix-{ticket.key.lower()}"
    workspace.commit(branch, f"Fix {ticket.key}")
    pr_url = context.repo_provider.open_draft_pr(
        ticket.repo, branch, f"Fix {ticket.key}", ""
    )
    context.tracker.add_comment(ticket.key, f"Draft Fix PR: {pr_url}")
    context.tracker.set_status(ticket.key, "In Review")
    report.pull_requests.append(pr_url)
    report.outcomes[ticket.key] = "fixed"
