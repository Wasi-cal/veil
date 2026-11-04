import posixpath

from veil.engine.constants.names import (
    BREAKING_HEADING,
    CHANGE_LABEL,
    COMMIT_FOOTER_KEY,
    COMMIT_PREFIX,
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
    """The title of the PR: the tickets first, then a short Conventional Commit.

    One fix: its ticket and its commit subject, for example "VT-10 | fix(security): replace eval".
    More fixes: every ticket, then the count and the file, for example
    "VT-1 | VT-2 | VT-3 | fix(security): resolve 3 findings in app.py".
    """
    keys = [fix.ticket.key for fix in fixes]
    head = " | ".join(keys)
    if len(keys) == 1:
        return f"{head} | {fixes[0].commit_message}"
    file = posixpath.basename(fixes[0].ticket.file.replace("\\", "/"))
    return f"{head} | {COMMIT_PREFIX}resolve {len(keys)} findings in {file}"


def pr_body(group: FixGroup, fixes: list[Fix]) -> str:
    """The body of the PR: one section for each Fix. A PR of several Fixes starts with the reason for the group.

    A section has the ticket and the place of the finding, then the three parts of the explanation.
    """
    sections = []
    if group.reason and len(fixes) > 1:
        sections.append(f"{SUMMARY_HEADING}\n\n{group.reason}")
    for fix in fixes:
        ticket = fix.ticket
        breaking = (
            f"**{BREAKING_HEADING}**\n{_reason_lines(fix)}\n\n" if fix.breaking else ""
        )
        sections.append(
            f"## {ticket.key} · `{ticket.file}:{ticket.line}`\n\n"
            f"{breaking}"
            f"**{PROBLEM_LABEL}**\n{fix.problem}\n\n"
            f"**{CHANGE_LABEL}**\n{fix.change}\n\n"
            f"**{SOLVES_LABEL}**\n{fix.solves}"
        )
    return "\n\n".join(sections)


def ticket_comment(pr_url: str, fix: Fix) -> str:
    """The comment on the ticket: the link to the PR, the breaking reason if there is one, then the three parts."""
    breaking = (
        f"{BREAKING_HEADING}: {' '.join(fix.breaking_reasons)}\n"
        if fix.breaking
        else ""
    )
    return (
        f"The Engine opened a Fix PR: {pr_url}\n"
        f"{breaking}"
        f"{PROBLEM_LABEL}: {fix.problem}\n"
        f"{CHANGE_LABEL}: {fix.change}\n"
        f"{SOLVES_LABEL}: {fix.solves}"
    )


def _reason_lines(fix: Fix) -> str:
    """One reason as plain text. Several reasons as a list, one line each."""
    if len(fix.breaking_reasons) == 1:
        return fix.breaking_reasons[0]
    return "\n".join(f"- {reason}" for reason in fix.breaking_reasons)
