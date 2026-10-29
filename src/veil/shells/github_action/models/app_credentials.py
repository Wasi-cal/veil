from pydantic import BaseModel, ConfigDict, SecretStr


class AppCredentials(BaseModel):
    """The GitHub App of the workflow. The Action mints its token from these two values."""

    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    app_id: str
    private_key: SecretStr
