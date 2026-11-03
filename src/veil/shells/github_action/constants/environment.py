# The variables that the GitHub runner sets for every Action.
REPOSITORY_VARIABLE = "GITHUB_REPOSITORY"
WORKSPACE_VARIABLE = "GITHUB_WORKSPACE"
EVENT_VARIABLE = "GITHUB_EVENT_NAME"
SUMMARY_VARIABLE = "GITHUB_STEP_SUMMARY"
# The file with the data of the event. The runner sets it. A pull request event has the head of the PR in it.
EVENT_PATH_VARIABLE = "GITHUB_EVENT_PATH"
# The largest event file that the Action reads.
EVENT_FILE_MAX_BYTES = 10 * 1024 * 1024

# The workflow gives the Action its GitHub token through this variable. The token covers this repo for this job only.
GITHUB_TOKEN_VARIABLE = "GITHUB_TOKEN"
