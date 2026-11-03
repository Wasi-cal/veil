# The events that may start a run. Each event has the setting that turns it on.
# A pull request from a fork never runs, even if its setting is on. It must never get a secret.
EVENT_SETTINGS = {
    "schedule": "schedule_enabled",
    "workflow_dispatch": "on_demand_enabled",
    "repository_dispatch": "event_enabled",
    "pull_request": "pull_request_enabled",
}
# A run on this event sees only the tickets of the branch of the pull request. A fork pull request never runs.
PULL_REQUEST_EVENT = "pull_request"
