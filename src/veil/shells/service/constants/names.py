# The task queue of the workers of the org-wide service.
TASK_QUEUE = "veil-task-queue"
# The workflow ID of a repo is this prefix and the repo name. A second start for a repo joins the first.
WORKFLOW_ID_PREFIX = "veil-run-"
READ_SETTINGS_ACTIVITY = "read_settings"
RUN_ENGINE_ACTIVITY = "run_engine"
# One worker runs at most this many activities at once. Each one runs in its own thread.
ACTIVITY_THREADS = 16
