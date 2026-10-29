from veil.engine.constants.outcomes import FIXED
from veil.engine.context import Context
from veil.engine.fix.pr_text import pr_body, ticket_comment
from veil.engine.models.fix.fix import Fix
from veil.engine.models.group.fix_group import FixGroup
from veil.engine.models.provider.draft_pr import DraftPr
from veil.engine.models.report.run_report import RunReport


def publish(
    context: Context,
    group: FixGroup,
    fixes: list[Fix],
    branch: str,
    report: RunReport,
) -> None:
    """Open one draft Fix PR for the Fixes of a group. Comment on each ticket and set In Review.

    The Fixes are already committed on the branch of the group.
    The Engine hides the credential values of this run in every text that it sends.
    """
    if not fixes:
        return
    keys = [fix.ticket.key for fix in fixes]
    draft = DraftPr(
        repo=group.repo,
        head=branch,
        base=group.branch,
        title=context.redact(group.title(keys)),
        body=context.redact(pr_body(group, fixes)),
        labels=tuple(label for fix in fixes if (label := fix.ticket.issue_label)),
    )
    pr_url = context.repo_provider.open_draft_pr(draft)
    for fix in fixes:
        context.tracker.add_comment(
            fix.ticket.key, context.redact(ticket_comment(pr_url, fix))
        )
        context.tracker.set_status(fix.ticket.key, context.settings.in_review_status)
        report.outcomes[fix.ticket.key] = FIXED
    report.pull_requests.append(pr_url)
