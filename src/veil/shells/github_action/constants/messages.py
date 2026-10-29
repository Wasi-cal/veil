NO_REPOSITORY = "The variable {name} is not set. The runner sets it."
BAD_REPOSITORY = "The variable {name} does not hold a repository name."
NO_WORKSPACE = "The variable {name} is not set. Run actions/checkout first."
UNSUPPORTED_EVENT = "The event {event} cannot start a run. Use schedule, workflow_dispatch or repository_dispatch."
TRIGGER_OFF = "Skipped the run. The event {event} is off. Turn on the setting {setting} to allow it."
APP_VARIABLE_MISSING = (
    "The variable {name} is not set. The Action needs the GitHub App."
)
CREDENTIAL_MISSING = "The variable {name} is not set or is empty."
CREDENTIAL_TOO_SHORT = "The variable {name} is too short to be a credential."
RESERVED_NAME = (
    "The setting {key} names {name}. The Action keeps that variable for itself."
)
SHARED_NAME = "The settings name one variable for more than one credential."
UNEXPECTED_ERROR = "The run stopped with an unexpected error."

SUMMARY_TITLE = "## Veil run"
SUMMARY_TOKENS = "Tokens used: {count}"
SUMMARY_PRS = "### Fix PRs"
SUMMARY_TICKETS = "### Tickets"
SUMMARY_SKIPPED = "### Skipped"
