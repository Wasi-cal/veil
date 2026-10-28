from typing import Literal

# The kind of Fix that the repo provider found. A kind is also the reason to skip the ticket.
FixKind = Literal["open_pr", "fix_branch"]

OPEN_PR: FixKind = "open_pr"
FIX_BRANCH: FixKind = "fix_branch"
