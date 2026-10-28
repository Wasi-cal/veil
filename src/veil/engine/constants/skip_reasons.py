from typing import Literal

# The kind of Fix that the repo provider found. A kind is also the reason to skip the ticket.
FixKind = Literal["open_pr", "fix_branch"]

RAISED_AGAINST_FIX_BRANCH = "raised_against_fix_branch"
FAILED_FIX = "failed_fix"
NO_ISSUE_LABEL = "no_issue_label"
DUPLICATE_ISSUE = "duplicate_issue"
SOURCE_PR_NOT_OPEN = "source_pr_not_open"
OPEN_PR: FixKind = "open_pr"
FIX_BRANCH: FixKind = "fix_branch"
