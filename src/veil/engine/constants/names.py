# Names that veil writes or reads: branches, labels, statuses, models, outcomes, kinds, severity and PR text.
from typing import Literal

# --- branches ---
FIX_BRANCH_PREFIX = "gozu/fix-"

# --- paths ---
# Gozu makes no ticket for a file in these directories. veil skips an older ticket that has one.
IGNORED_DIRECTORIES = frozenset({".github"})

# --- labels ---
ISSUE_LABEL_PREFIX = "issue-"
FAILED_FIX_LABEL = "veil-failed-fix"
# The label that marks a Gozu Ticket as one that the Engine may fix. A setting can change it.
DEFAULT_ELIGIBLE_LABEL = "veil-eligible"

# --- statuses ---
IN_REVIEW = "In Review"

# --- model_names ---
# The names are the small cheap model and a mid-tier model of OpenAI, not the flagship. A setting can change them.
CHEAP_MODEL = "gpt-6-luna"
STRONG_MODEL = "gpt-6.1-terra"

# --- credential_names ---
# The default names of the environment variables that hold the credentials of a Shell that reads them from the environment.
DEFAULT_JIRA_EMAIL_ENV = "JIRA_EMAIL"
DEFAULT_JIRA_TOKEN_ENV = "JIRA_API_TOKEN"
DEFAULT_OPENAI_KEY_ENV = "OPENAI_API_KEY"

# --- outcomes ---
FIXED = "fixed"
FAILED = "failed"
LEFT_FOR_NEXT_RUN = "left_for_next_run"
SKIPPED = "skipped"

# Why a run stopped before it handled every ticket.
STOPPED_TOKEN_EXPIRED = "token_expired"

# --- skip_reasons ---
RAISED_AGAINST_FIX_BRANCH = "raised_against_fix_branch"
FAILED_FIX = "failed_fix"
NO_ISSUE_LABEL = "no_issue_label"
IGNORED_PATH = "ignored_path"
DUPLICATE_ISSUE = "duplicate_issue"
SOURCE_PR_NOT_OPEN = "source_pr_not_open"

# --- fix_kinds ---
# The kind of Fix that the repo provider found. A kind is also the reason to skip the ticket.
FixKind = Literal["open_pr", "merged_pr", "fix_branch"]

OPEN_PR: FixKind = "open_pr"
MERGED_PR: FixKind = "merged_pr"
FIX_BRANCH: FixKind = "fix_branch"

# --- severity ---
Bucket = Literal["high", "medium", "low"]

HIGH: Bucket = "high"
MEDIUM: Bucket = "medium"
LOW: Bucket = "low"

# The order in which the groups run. A budget that ends the run first spares the High tickets.
BUCKET_RANK: dict[Bucket, int] = {HIGH: 0, MEDIUM: 1, LOW: 2}

# Gozu uses the Sonar words. The plain words map to themselves.
DEFAULT_SEVERITY_MAP: dict[str, Bucket] = {
    "BLOCKER": HIGH,
    "CRITICAL": HIGH,
    "MAJOR": MEDIUM,
    "MINOR": LOW,
    "INFO": LOW,
    "HIGH": HIGH,
    "MEDIUM": MEDIUM,
    "LOW": LOW,
}

# --- pr_text ---
# The labels of the three parts of the explanation of a Fix. They stay the same in the PR and in the ticket comment.
PROBLEM_LABEL = "Why this is a problem"
CHANGE_LABEL = "What changed"
SOLVES_LABEL = "What this solves"

# --- the standard of commits and PRs ---
# A commit subject is a Conventional Commit: "fix(security): replace eval with a safe parser".
COMMIT_PREFIX = "fix(security): "
COMMIT_SUBJECT_MAX_LENGTH = 72
COMMIT_FOOTER_KEY = "Refs"
SUMMARY_HEADING = "## Summary"
