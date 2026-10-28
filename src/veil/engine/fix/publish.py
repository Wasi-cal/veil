from veil.engine.constants.outcomes import FIXED
from veil.engine.constants.statuses import IN_REVIEW
from veil.engine.context import Context
from veil.engine.models.fix.fix import Fix
from veil.engine.models.group.fix_group import FixGroup
from veil.engine.models.provider.draft_pr import DraftPr
from veil.engine.models.report.run_report import RunReport


def branch_name(group: FixGroup, first_fixed: Fix, prefix: str) -> str:
    """The branch of the Fix PR of a group. It starts with the branch prefix and names the first Fix that passed.

    A ticket that failed gives no name. A later run can then make a new PR for that ticket without a branch clash.
    """
    key = first_fixed.ticket.key.lower()
    return f"{prefix}{key}" if group.kind == "high" else f"{prefix}shared-{key}"


def publish(
    context: Context,
    group: FixGroup,
    fixes: list[Fix],
    branch: str,
    report: RunReport,
) -> None:
    """Open one draft Fix PR for the Fixes of a group. Comment on each ticket and set In Review.

    The Fixes are already committed on the branch of the group.
    """
    if not fixes:
        return
    keys = [fix.ticket.key for fix in fixes]
    draft = DraftPr(
        repo=group.repo,
        head=branch,
        base=group.branch,
        title=f"Fix {', '.join(keys)}"
        if group.kind == "high"
        else f"Fix {len(keys)} tickets",
        body=_body(group, fixes),
        labels=tuple(label for fix in fixes if (label := fix.ticket.issue_label)),
    )
    pr_url = context.repo_provider.open_draft_pr(draft)
    for fix in fixes:
        context.tracker.add_comment(
            fix.ticket.key,
            f"The Engine opened a draft Fix PR: {pr_url}\n{fix.explanation}",
        )
        context.tracker.set_status(fix.ticket.key, IN_REVIEW)
        report.outcomes[fix.ticket.key] = FIXED
    report.pull_requests.append(pr_url)


def _body(group: FixGroup, fixes: list[Fix]) -> str:
    """The body of the PR: the reason for the group, then the explanation of each Fix."""
    parts = [f"{fix.ticket.key}: {fix.explanation}" for fix in fixes]
    if group.reason:
        parts.insert(0, group.reason)
    return "\n\n".join(parts)
