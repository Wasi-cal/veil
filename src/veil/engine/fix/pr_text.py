from veil.engine.models.fix.fix import Fix
from veil.engine.models.group.fix_group import FixGroup


def pr_body(group: FixGroup, fixes: list[Fix]) -> str:
    """The body of the PR: the reason for the group, then the explanation of each Fix.

    The reason names the Fixes that share the PR. It has no use if only one Fix passed.
    """
    parts = [f"{fix.ticket.key}: {fix.explanation}" for fix in fixes]
    if group.reason and len(fixes) > 1:
        parts.insert(0, group.reason)
    return "\n\n".join(parts)


def ticket_comment(pr_url: str, fix: Fix) -> str:
    """The comment on the ticket: the link to the PR, then the explanation."""
    return f"The Engine opened a draft Fix PR: {pr_url}\n{fix.explanation}"
