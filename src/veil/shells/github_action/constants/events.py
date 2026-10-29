# The events that may start a run. Each event has the setting that turns it on.
# A fork pull request is not on the list. It must never get a secret.
EVENT_SETTINGS = {
    "schedule": "schedule_enabled",
    "workflow_dispatch": "on_demand_enabled",
    "repository_dispatch": "event_enabled",
}
