from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

from veil.engine.constants.limits import MIN_SECRET_LENGTH
from veil.engine.interfaces.model_client import ModelClient
from veil.engine.interfaces.repo_provider import RepoProvider
from veil.engine.interfaces.tracker import Tracker
from veil.engine.models.config.settings import Settings
from veil.engine.secrets.redact import redact


class Context(BaseModel):
    # A validation error must never repeat a credential value.
    model_config = ConfigDict(
        frozen=True, arbitrary_types_allowed=True, hide_input_in_errors=True
    )

    settings: Settings
    tracker: Tracker
    repo_provider: RepoProvider
    model_client: ModelClient
    credentials: tuple[SecretStr, ...] = ()

    @field_validator("credentials")
    @classmethod
    def _long_enough(cls, credentials: tuple[SecretStr, ...]) -> tuple[SecretStr, ...]:
        """A short value or a blank value would change normal text when the Engine redacts.

        The message never shows a value.
        """
        values = [credential.get_secret_value() for credential in credentials]
        if any(len(value) < MIN_SECRET_LENGTH for value in values):
            raise ValueError(
                f"A credential value must have at least {MIN_SECRET_LENGTH} characters."
            )
        if any(not value.strip() for value in values):
            raise ValueError("A credential value must not be only white space.")
        return credentials

    def redact(self, text: str) -> str:
        """Replace the credential values of this run, and the known secret patterns, in a text.

        Use it on every text that leaves the Engine.
        """
        return redact(text, self.credential_values)

    @property
    def credential_values(self) -> tuple[str, ...]:
        """The credential values of this run, as plain text. Use them only to scan and to redact."""
        return tuple(value.get_secret_value() for value in self.credentials)
