from pydantic import BaseModel, ConfigDict, SecretStr


class ActionCredentials(BaseModel):
    """The credentials that the Action reads from the environment. The GitHub token is not here. The Action mints it."""

    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    jira_email: str | None
    jira_token: SecretStr
    openai_key: SecretStr
