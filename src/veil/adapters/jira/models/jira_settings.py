from pydantic import BaseModel, ConfigDict, Field, field_validator

from veil.adapters.jira.constants.patterns import PROJECT_KEY, SAFE_LABEL
from veil.engine.constants.labels import DEFAULT_ELIGIBLE_LABEL
from veil.engine.errors.settings_error import SettingsError
from veil.engine.models.config.settings import Settings


class JiraSettings(BaseModel):
    """Where the tickets are and which of them the Engine may fix. These values are not secret.

    An empty `eligible_label` means that a ticket needs no label.

    The credentials never come from settings. The Shell passes them in.
    """

    model_config = ConfigDict(frozen=True)

    site_url: str
    project_keys: tuple[str, ...] = Field(min_length=1)
    eligible_label: str = DEFAULT_ELIGIBLE_LABEL

    @classmethod
    def from_settings(cls, settings: Settings) -> "JiraSettings":
        """The Jira settings of a run. The site and the project keys must be set."""
        problems = [
            f"{key} is empty. The Jira tracker needs it."
            for key, value in (
                ("jira_site_url", settings.jira_site_url),
                ("jira_project_keys", settings.jira_project_keys),
            )
            if not value
        ]
        if problems:
            raise SettingsError(problems)
        return cls(
            site_url=settings.jira_site_url,
            project_keys=settings.jira_project_keys,
            eligible_label=settings.eligible_label,
        )

    @field_validator("project_keys")
    @classmethod
    def _safe_project_keys(cls, keys: tuple[str, ...]) -> tuple[str, ...]:
        if not all(PROJECT_KEY.fullmatch(key) for key in keys):
            raise ValueError("A project key has capital letters, digits and _ only.")
        return keys

    @field_validator("eligible_label")
    @classmethod
    def _safe_label(cls, label: str) -> str:
        if label and not SAFE_LABEL.fullmatch(label):
            raise ValueError("The eligible label has no space, quote or backslash.")
        return label
