from veil.engine.models.config.settings import Settings
from veil.shells.github_action.constants.events import EVENT_SETTINGS
from veil.shells.github_action.constants.messages import TRIGGER_OFF, UNSUPPORTED_EVENT
from veil.shells.github_action.errors.action_failure import ActionFailure


def skip_reason(event: str, settings: Settings) -> str | None:
    """Return why this event must not start a run, or None if it may.

    An event that is not on the list raises ActionFailure. A fork pull request is never on the list.
    """
    setting = EVENT_SETTINGS.get(event)
    if setting is None:
        raise ActionFailure(UNSUPPORTED_EVENT.format(event=event or "(none)"))
    if getattr(settings, setting):
        return None
    return TRIGGER_OFF.format(event=event, setting=setting)
