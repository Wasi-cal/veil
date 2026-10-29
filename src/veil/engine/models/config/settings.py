import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from veil.engine.constants.branches import FIX_BRANCH_PREFIX
from veil.engine.constants.labels import DEFAULT_ELIGIBLE_LABEL, FAILED_FIX_LABEL
from veil.engine.constants.limits import (
    DIFF_LIMIT,
    EXPLANATION_MAX_SENTENCES,
    MAX_ATTEMPTS,
    MIN_TOOL_RESULT_MAX_BYTES,
    MODEL_CALLS_PER_MINUTE,
    READ_FILE_MAX_LINES,
    SEARCH_MAX_MATCHES,
    SHARED_PR_MAX,
    STEP_CAP,
    TOKEN_CEILING,
    TOOL_RESULT_MAX_BYTES,
)
from veil.engine.constants.model_names import CHEAP_MODEL, STRONG_MODEL
from veil.engine.constants.secrets import SECRET_PATTERNS
from veil.engine.constants.service_limits import (
    CACHE_JIRA_METADATA_TTL_SECONDS,
    CACHE_REPO_LIST_TTL_SECONDS,
    CACHE_SETTINGS_TTL_SECONDS,
    CHECKOUT_SWEEP_MINUTES,
    HEARTBEAT_SECONDS,
    MAX_CONCURRENT_RUNS,
    QUIET_WINDOW_MINUTES,
    RUN_TIMEOUT_MINUTES,
)
from veil.engine.constants.settings_bounds import (
    MAX_ENTRY_CHARS,
    MAX_LIST_ENTRIES,
    MAX_NAME_CHARS,
    MAX_URL_CHARS,
)
from veil.engine.constants.settings_patterns import (
    BRANCH_PREFIX,
    CRON,
    LABEL,
    PROJECT_KEY,
    REPO,
    SITE_URL,
)
from veil.engine.constants.settings_rules import (
    READER_ENGINE,
    READER_SHELL,
    TIGHTEN_ADD_ONLY,
    TIGHTEN_DISABLE_ONLY,
    TIGHTEN_FREE,
    TIGHTEN_LOCKED,
    TIGHTEN_LOWER,
    TIGHTEN_RAISE_ONLY,
)
from veil.engine.constants.severity import DEFAULT_SEVERITY_MAP, Bucket
from veil.engine.constants.statuses import IN_REVIEW
from veil.engine.constants.triggers import (
    EVENT_ENABLED,
    ON_DEMAND_ENABLED,
    SCHEDULE_CRON,
    SCHEDULE_ENABLED,
)


def _setting(default: Any, tighten: str, reader: str, **constraints: Any) -> Any:
    """One setting. The default, the bounds and the rule for a repo are in one place.

    The settings catalog reads them from here.
    """
    extra: dict[str, Any] = {"tighten": tighten, "reader": reader}
    if "default_factory" in constraints:
        return Field(json_schema_extra=extra, **constraints)
    return Field(default=default, json_schema_extra=extra, **constraints)


class Settings(BaseModel):
    """Every setting of a run. The defaults are in code. A layer can give other values.

    Settings hold no secret. The safety rules are code and are not here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # The fix loop
    cheap_model: str = _setting(
        CHEAP_MODEL,
        TIGHTEN_FREE,
        READER_ENGINE,
        min_length=1,
        max_length=MAX_NAME_CHARS,
    )
    strong_model: str = _setting(
        STRONG_MODEL,
        TIGHTEN_FREE,
        READER_ENGINE,
        min_length=1,
        max_length=MAX_NAME_CHARS,
    )
    max_attempts: int = _setting(MAX_ATTEMPTS, TIGHTEN_LOWER, READER_ENGINE, ge=1, le=2)
    step_cap: int = _setting(STEP_CAP, TIGHTEN_LOWER, READER_ENGINE, ge=1, le=100)
    diff_limit: int = _setting(DIFF_LIMIT, TIGHTEN_LOWER, READER_ENGINE, ge=0, le=2000)
    tool_result_max_bytes: int = _setting(
        TOOL_RESULT_MAX_BYTES,
        TIGHTEN_LOWER,
        READER_ENGINE,
        ge=MIN_TOOL_RESULT_MAX_BYTES,
        le=65_536,
    )
    read_file_max_lines: int = _setting(
        READ_FILE_MAX_LINES, TIGHTEN_LOWER, READER_ENGINE, ge=1, le=2000
    )
    search_max_matches: int = _setting(
        SEARCH_MAX_MATCHES, TIGHTEN_LOWER, READER_ENGINE, ge=1, le=500
    )
    explanation_max_sentences: int = _setting(
        EXPLANATION_MAX_SENTENCES, TIGHTEN_LOWER, READER_ENGINE, ge=1, le=10
    )
    extra_refused_read_patterns: tuple[str, ...] = _setting(
        (), TIGHTEN_ADD_ONLY, READER_ENGINE, max_length=MAX_LIST_ENTRIES
    )

    # The budget
    token_ceiling: int = _setting(
        TOKEN_CEILING, TIGHTEN_LOWER, READER_ENGINE, ge=1, le=5_000_000
    )
    model_calls_per_minute: int = _setting(
        MODEL_CALLS_PER_MINUTE, TIGHTEN_LOWER, READER_SHELL, ge=1, le=600
    )

    # Grouping and the names that the Engine writes
    shared_pr_max: int = _setting(
        SHARED_PR_MAX, TIGHTEN_LOWER, READER_ENGINE, ge=1, le=50
    )
    branch_prefix: str = _setting(
        FIX_BRANCH_PREFIX,
        TIGHTEN_LOCKED,
        READER_ENGINE,
        min_length=3,
        max_length=MAX_NAME_CHARS,
        pattern=BRANCH_PREFIX,
    )
    severity_map: dict[str, Bucket] = _setting(
        None,
        TIGHTEN_RAISE_ONLY,
        READER_ENGINE,
        default_factory=lambda: dict(DEFAULT_SEVERITY_MAP),
    )
    eligible_label: str = _setting(
        DEFAULT_ELIGIBLE_LABEL,
        TIGHTEN_FREE,
        READER_SHELL,
        pattern=LABEL,
        max_length=MAX_NAME_CHARS,
    )
    failed_fix_label: str = _setting(
        FAILED_FIX_LABEL,
        TIGHTEN_FREE,
        READER_ENGINE,
        pattern=LABEL,
        max_length=MAX_NAME_CHARS,
    )
    in_review_status: str = _setting(
        IN_REVIEW, TIGHTEN_LOCKED, READER_ENGINE, min_length=1, max_length=60
    )

    # The tracker and the repos that the Shells use
    jira_site_url: str = _setting(
        "", TIGHTEN_LOCKED, READER_SHELL, pattern=SITE_URL, max_length=MAX_URL_CHARS
    )
    jira_project_keys: tuple[str, ...] = _setting(
        (), TIGHTEN_LOCKED, READER_SHELL, max_length=MAX_LIST_ENTRIES
    )
    repos_allow: tuple[str, ...] = _setting(
        (), TIGHTEN_LOCKED, READER_SHELL, max_length=MAX_LIST_ENTRIES
    )
    repos_deny: tuple[str, ...] = _setting(
        (), TIGHTEN_LOCKED, READER_SHELL, max_length=MAX_LIST_ENTRIES
    )

    # The triggers
    schedule_enabled: bool = _setting(
        SCHEDULE_ENABLED, TIGHTEN_DISABLE_ONLY, READER_SHELL
    )
    schedule_cron: str = _setting(
        SCHEDULE_CRON,
        TIGHTEN_LOCKED,
        READER_SHELL,
        pattern=CRON,
        max_length=MAX_NAME_CHARS,
    )
    on_demand_enabled: bool = _setting(
        ON_DEMAND_ENABLED, TIGHTEN_DISABLE_ONLY, READER_SHELL
    )
    event_enabled: bool = _setting(EVENT_ENABLED, TIGHTEN_DISABLE_ONLY, READER_SHELL)

    # The timings of the service
    quiet_window_minutes: int = _setting(
        QUIET_WINDOW_MINUTES, TIGHTEN_LOCKED, READER_SHELL, ge=0, le=120
    )
    run_timeout_minutes: int = _setting(
        RUN_TIMEOUT_MINUTES, TIGHTEN_LOWER, READER_SHELL, ge=1, le=240
    )
    heartbeat_seconds: int = _setting(
        HEARTBEAT_SECONDS, TIGHTEN_LOCKED, READER_SHELL, ge=10, le=600
    )
    max_concurrent_runs: int = _setting(
        MAX_CONCURRENT_RUNS, TIGHTEN_LOWER, READER_SHELL, ge=1, le=20
    )
    checkout_sweep_minutes: int = _setting(
        CHECKOUT_SWEEP_MINUTES, TIGHTEN_LOCKED, READER_SHELL, ge=10, le=1440
    )

    # The cache lifetimes
    cache_settings_ttl_seconds: int = _setting(
        CACHE_SETTINGS_TTL_SECONDS, TIGHTEN_LOCKED, READER_SHELL, ge=1, le=86_400
    )
    cache_jira_metadata_ttl_seconds: int = _setting(
        CACHE_JIRA_METADATA_TTL_SECONDS, TIGHTEN_LOCKED, READER_SHELL, ge=1, le=86_400
    )
    cache_repo_list_ttl_seconds: int = _setting(
        CACHE_REPO_LIST_TTL_SECONDS, TIGHTEN_LOCKED, READER_SHELL, ge=1, le=86_400
    )

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

    @field_validator(
        "extra_refused_read_patterns", "jira_project_keys", "repos_allow", "repos_deny"
    )
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

    @field_validator("repos_allow", "repos_deny")
    @classmethod
    def _repo_names(cls, names: tuple[str, ...]) -> tuple[str, ...]:
        return _each_matches(names, REPO, "a repository name")


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
