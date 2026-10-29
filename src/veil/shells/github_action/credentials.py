from collections.abc import Mapping

from pydantic import SecretStr

from veil.engine.constants.limits import MIN_SECRET_LENGTH
from veil.engine.models.config.settings import Settings
from veil.shells.github_action.constants.credential_env import RESERVED_PREFIXES
from veil.shells.github_action.constants.environment import (
    APP_ID_VARIABLE,
    APP_KEY_VARIABLE,
)
from veil.shells.github_action.constants.messages import (
    APP_VARIABLE_MISSING,
    CREDENTIAL_MISSING,
    CREDENTIAL_TOO_SHORT,
    RESERVED_NAME,
    SHARED_NAME,
)
from veil.shells.github_action.errors.action_failure import ActionFailure
from veil.shells.github_action.models.action_credentials import ActionCredentials
from veil.shells.github_action.models.app_credentials import AppCredentials


def read_credentials(
    environ: Mapping[str, str], settings: Settings
) -> ActionCredentials:
    """Read the Jira and OpenAI credentials from the variables that the settings name.

    A setting may not name a variable that the Action or the runner owns. Two credentials may not share a variable.
    A missing or short value raises ActionFailure. The message names the variable and never shows a value.
    """
    names = {
        "jira_email_env": settings.jira_email_env,
        "jira_token_env": settings.jira_token_env,
        "openai_key_env": settings.openai_key_env,
    }
    for key, name in names.items():
        if name.startswith(RESERVED_PREFIXES):
            raise ActionFailure(RESERVED_NAME.format(key=key, name=name))
    if len(set(names.values())) != len(names):
        raise ActionFailure(SHARED_NAME)
    return ActionCredentials(
        jira_email=(environ.get(settings.jira_email_env) or "").strip() or None,
        jira_token=_secret(environ, settings.jira_token_env),
        openai_key=_secret(environ, settings.openai_key_env),
    )


def _secret(environ: Mapping[str, str], name: str) -> SecretStr:
    value = environ.get(name, "")
    if not value.strip():
        raise ActionFailure(CREDENTIAL_MISSING.format(name=name))
    if len(value) < MIN_SECRET_LENGTH:
        raise ActionFailure(CREDENTIAL_TOO_SHORT.format(name=name))
    return SecretStr(value)


def read_app_credentials(environ: Mapping[str, str]) -> AppCredentials:
    """Read the GitHub App id and private key. A missing value raises ActionFailure that names the variable."""
    values = {}
    for name in (APP_ID_VARIABLE, APP_KEY_VARIABLE):
        values[name] = environ.get(name, "")
        if not values[name].strip():
            raise ActionFailure(APP_VARIABLE_MISSING.format(name=name))
    return AppCredentials(
        app_id=values[APP_ID_VARIABLE],
        private_key=SecretStr(values[APP_KEY_VARIABLE]),
    )
