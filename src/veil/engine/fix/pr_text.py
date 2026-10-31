from veil.engine.constants.names import (
    CHANGE_LABEL,
    COMMIT_FOOTER_KEY,
    COMMIT_PREFIX,
    PR_TITLE_KEYS_SHOWN,
    PROBLEM_LABEL,
    SOLVES_LABEL,
    SUMMARY_HEADING,
)
from veil.engine.models.fix.fix import Fix
from veil.engine.models.group.fix_group import FixGroup


def commit_text(fix: Fix) -> str:
    """The commit message: the subject of the model, then a footer that names the ticket."""
    return f"{fix.commit_message}\n\n{COMMIT_FOOTER_KEY}: {fix.ticket.key}"


def pr_title(fixes: list[Fix]) -> str:
    """The title of the PR, in the form of a Conventional Commit.

    One fix: its commit subject and its ticket, for example "fix(security): replace eval (VT-10)".
    More fixes: the count and the tickets, for example "fix(security): resolve 3 findings (VT-1, VT-2, VT-3)".
    """
    keys = [fix.ticket.key for fix in fixes]
    if len(keys) == 1:
        return f"{fixes[0].commit_message} ({keys[0]})"
    shown = ", ".join(keys[:PR_TITLE_KEYS_SHOWN])
    rest = len(keys) - PR_TITLE_KEYS_SHOWN
    names = shown if rest <= 0 else f"{shown} and {rest} more"
    return f"{COMMIT_PREFIX}resolve {len(keys)} findings ({names})"


def pr_body(group: FixGroup, fixes: list[Fix]) -> str:
    """The body of the PR: one section for each Fix. A PR of several Fixes starts with the reason for the group.

    A section has the ticket and the place of the finding, then the three parts of the explanation.
    """
    sections = []
    if group.reason and len(fixes) > 1:
        sections.append(f"{SUMMARY_HEADING}\n\n{group.reason}")
    for fix in fixes:
        ticket = fix.ticket
        sections.append(
            f"## {ticket.key} · `{ticket.file}:{ticket.line}`\n\n"
            f"**{PROBLEM_LABEL}**\n{fix.problem}\n\n"
            f"**{CHANGE_LABEL}**\n{fix.change}\n\n"
            f"**{SOLVES_LABEL}**\n{fix.solves}"
        )
    return "\n\n".join(sections)


def ticket_comment(pr_url: str, fix: Fix) -> str:
    """The comment on the ticket: the link to the PR, then the three parts."""
    return (
        f"The Engine opened a Fix PR: {pr_url}\n"
        f"{PROBLEM_LABEL}: {fix.problem}\n"
        f"{CHANGE_LABEL}: {fix.change}\n"
        f"{SOLVES_LABEL}: {fix.solves}"
    )
