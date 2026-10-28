from pydantic import BaseModel, ConfigDict, SecretStr


class JiraCredentials(BaseModel):
    """What the Shell gives the adapter. An email and a token use basic authentication.

    A token with no email is a bearer token.
    """

    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    email: str | None = None
    api_token: SecretStr
