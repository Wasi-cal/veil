from pydantic import BaseModel, ConfigDict, SecretStr


class RunCredentials(BaseModel):
    """The Jira and OpenAI credentials of a run. The GitHub token is not here. A Shell mints it."""

    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    jira_email: str | None
    jira_token: SecretStr
    openai_key: SecretStr
