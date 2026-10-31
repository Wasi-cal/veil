import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from veil.engine.constants.limits import (
    DIFF_LIMIT,
    EVENT_ENABLED,
    EXPLANATION_MAX_SENTENCES,
    MAX_ATTEMPTS,
    MAX_ENTRY_CHARS,
    MAX_LIST_ENTRIES,
    MAX_NAME_CHARS,
    MAX_URL_CHARS,
    MIN_TOOL_RESULT_MAX_BYTES,
    ON_DEMAND_ENABLED,
    READ_FILE_MAX_LINES,
    SCHEDULE_ENABLED,
    SEARCH_MAX_MATCHES,
    SHARED_PR_MAX,
    STEP_CAP,
    TOKEN_CEILING,
    TOOL_RESULT_MAX_BYTES,
)
from veil.engine.constants.names import (
    CHEAP_MODEL,
    DEFAULT_ELIGIBLE_LABEL,
    DEFAULT_JIRA_EMAIL_ENV,
    DEFAULT_JIRA_TOKEN_ENV,
    DEFAULT_OPENAI_KEY_ENV,
    DEFAULT_SEVERITY_MAP,
    FAILED_FIX_LABEL,
    FIX_BRANCH_PREFIX,
    IN_REVIEW,
    STRONG_MODEL,
    Bucket,
)
from veil.engine.constants.safety import SECRET_PATTERNS
from veil.engine.constants.settings_text import (
    BRANCH_PREFIX,
    ENV_NAME,
    LABEL,
    OPTIONAL_LABEL,
    PROJECT_KEY,
    SITE_URL,
)


class Settings(BaseModel):
    """Every setting of a run. The defaults are in code. The repo file can give other values.

    Settings hold no secret. The safety rules are code and are not here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # The fix loop
    cheap_model: str = Field(
        default=CHEAP_MODEL,
        min_length=1,
        max_length=MAX_NAME_CHARS,
    )
    strong_model: str = Field(
        default=STRONG_MODEL,
        min_length=1,
        max_length=MAX_NAME_CHARS,
    )
    max_attempts: int = Field(default=MAX_ATTEMPTS, ge=1, le=2)
    step_cap: int = Field(default=STEP_CAP, ge=1, le=100)
    diff_limit: int = Field(default=DIFF_LIMIT, ge=0, le=2000)
    tool_result_max_bytes: int = Field(
        default=TOOL_RESULT_MAX_BYTES,
        ge=MIN_TOOL_RESULT_MAX_BYTES,
        le=65_536,
    )
    read_file_max_lines: int = Field(default=READ_FILE_MAX_LINES, ge=1, le=2000)
    search_max_matches: int = Field(default=SEARCH_MAX_MATCHES, ge=1, le=500)
    explanation_max_sentences: int = Field(
        default=EXPLANATION_MAX_SENTENCES, ge=1, le=10
    )
    extra_refused_read_patterns: tuple[str, ...] = Field(
        default=(), max_length=MAX_LIST_ENTRIES
    )

    # The budget
    token_ceiling: int = Field(default=TOKEN_CEILING, ge=1, le=5_000_000)

    # Grouping and the names that the Engine writes
    shared_pr_max: int = Field(default=SHARED_PR_MAX, ge=1, le=50)
    branch_prefix: str = Field(
        default=FIX_BRANCH_PREFIX,
        min_length=3,
        max_length=MAX_NAME_CHARS,
        pattern=BRANCH_PREFIX,
    )
    severity_map: dict[str, Bucket] = Field(
        default_factory=lambda: dict(DEFAULT_SEVERITY_MAP),
    )
    eligible_label: str = Field(
        default=DEFAULT_ELIGIBLE_LABEL,
        pattern=OPTIONAL_LABEL,
        max_length=MAX_NAME_CHARS,
    )
    failed_fix_label: str = Field(
        default=FAILED_FIX_LABEL,
        pattern=LABEL,
        max_length=MAX_NAME_CHARS,
    )
    in_review_status: str = Field(default=IN_REVIEW, min_length=1, max_length=60)

    # The tracker and the repos that the Shells use
    jira_site_url: str = Field(default="", pattern=SITE_URL, max_length=MAX_URL_CHARS)
    jira_project_keys: tuple[str, ...] = Field(default=(), max_length=MAX_LIST_ENTRIES)
    # The names of the environment variables that hold the credentials. A value is never a setting.
    jira_email_env: str = Field(
        default=DEFAULT_JIRA_EMAIL_ENV,
        pattern=ENV_NAME,
        max_length=MAX_NAME_CHARS,
    )
    jira_token_env: str = Field(
        default=DEFAULT_JIRA_TOKEN_ENV,
        pattern=ENV_NAME,
        max_length=MAX_NAME_CHARS,
    )
    openai_key_env: str = Field(
        default=DEFAULT_OPENAI_KEY_ENV,
        pattern=ENV_NAME,
        max_length=MAX_NAME_CHARS,
    )

    # The triggers
    schedule_enabled: bool = Field(default=SCHEDULE_ENABLED)
    on_demand_enabled: bool = Field(default=ON_DEMAND_ENABLED)
    event_enabled: bool = Field(default=EVENT_ENABLED)

    @field_validator("branch_prefix")
    @classmethod
    def _safe_branch_prefix(cls, value: str) -> str:
        """Refuse a prefix that Git can read as a path trick or as an option."""
        if any(part in value for part in ("..", "//", "/.")):
            raise ValueError("branch_prefix must not hold '..', '//' or '/.'.")
        return value

    @field_validator("severity_map")
    @classmethod
    def _merge_with_defaults(cls, value: dict[str, Bucket]) -> dict[str, Bucket]:
        """Keep the default words. The given words replace the default bucket of the same word."""
        words = [word.strip().upper() for word in value]
        if len(set(words)) != len(words):
            raise PydanticCustomError("word_twice", "A severity word is there twice.")
        merged = dict(DEFAULT_SEVERITY_MAP)
        merged.update(dict(zip(words, value.values(), strict=True)))
        return merged

    @field_validator("extra_refused_read_patterns", "jira_project_keys")
    @classmethod
    def _short_entries(cls, entries: tuple[str, ...]) -> tuple[str, ...]:
        if any(len(entry) > MAX_ENTRY_CHARS for entry in entries):
            raise PydanticCustomError("entry_too_long", "An entry is too long.")
        return entries

    @model_validator(mode="after")
    def _no_secret_text(self) -> "Settings":
        """Settings hold no secret. This holds even when a caller builds Settings without the layers."""
        for name in type(self).model_fields:
            if secret_kind_in(getattr(self, name)):
                raise PydanticCustomError(
                    "secret_text", "A setting holds text that looks like a secret."
                )
        return self

    @field_validator("jira_project_keys")
    @classmethod
    def _project_keys(cls, keys: tuple[str, ...]) -> tuple[str, ...]:
        return _each_matches(keys, PROJECT_KEY, "a project key")


def secret_kind_in(value: Any) -> str | None:
    """The kind of secret that a text in the value looks like, or None. The kind never holds the text."""
    if isinstance(value, str):
        return next(
            (kind for kind, pattern in SECRET_PATTERNS if pattern.search(value)), None
        )
    if isinstance(value, Mapping):
        value = [*value.keys(), *value.values()]
    if isinstance(value, list | tuple):
        return next((kind for item in value if (kind := secret_kind_in(item))), None)
    return None


def _each_matches(values: tuple[str, ...], pattern: str, what: str) -> tuple[str, ...]:
    if not all(re.fullmatch(pattern, value) for value in values):
        raise ValueError(f"Each entry must be {what}.")
    return values
