from pydantic import BaseModel, ConfigDict, Field, field_validator

from veil.adapters.jira.constants.patterns import PROJECT_KEY, SAFE_LABEL
from veil.adapters.jira.constants.workflow import DEFAULT_ELIGIBLE_LABEL


class JiraSettings(BaseModel):
    """Where the tickets are and which of them the Engine may fix. These values are not secret.

    The credentials never come from settings. The Shell passes them in.
    """

    model_config = ConfigDict(frozen=True)

    site_url: str
    project_keys: tuple[str, ...] = Field(min_length=1)
    eligible_label: str = DEFAULT_ELIGIBLE_LABEL
    # The Engine says "In Review". A workflow can name that status another way. Map the name here.
    status_names: dict[str, str] = Field(default_factory=dict)

    @field_validator("project_keys")
    @classmethod
    def _safe_project_keys(cls, keys: tuple[str, ...]) -> tuple[str, ...]:
        if not all(PROJECT_KEY.fullmatch(key) for key in keys):
            raise ValueError("A project key has capital letters, digits and _ only.")
        return keys

    @field_validator("eligible_label")
    @classmethod
    def _safe_label(cls, label: str) -> str:
        if not SAFE_LABEL.fullmatch(label):
            raise ValueError("The eligible label has no space, quote or backslash.")
        return label
