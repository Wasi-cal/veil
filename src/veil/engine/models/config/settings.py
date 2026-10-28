from pydantic import BaseModel, ConfigDict, Field, field_validator

from veil.engine.constants.branches import FIX_BRANCH_PREFIX
from veil.engine.constants.limits import (
    DIFF_LIMIT,
    EXPLANATION_MAX_SENTENCES,
    READ_FILE_MAX_LINES,
    SEARCH_MAX_MATCHES,
    SHARED_PR_MAX,
    STEP_CAP,
    TOKEN_CEILING,
    TOOL_RESULT_MAX_BYTES,
)
from veil.engine.constants.models import CHEAP_MODEL, STRONG_MODEL
from veil.engine.constants.severity import DEFAULT_SEVERITY_MAP, Bucket


class Settings(BaseModel):
    """The defaults are in code. The caller can give other values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cheap_model: str = Field(default=CHEAP_MODEL, min_length=1)
    strong_model: str = Field(default=STRONG_MODEL, min_length=1)
    token_ceiling: int = Field(default=TOKEN_CEILING, ge=1)
    shared_pr_max: int = Field(default=SHARED_PR_MAX, ge=1)
    branch_prefix: str = Field(
        default=FIX_BRANCH_PREFIX,
        min_length=3,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*[/-]$",
    )
    severity_map: dict[str, Bucket] = Field(
        default_factory=lambda: dict(DEFAULT_SEVERITY_MAP)
    )
    step_cap: int = Field(default=STEP_CAP, ge=1)
    explanation_max_sentences: int = Field(default=EXPLANATION_MAX_SENTENCES, ge=1)
    diff_limit: int = Field(default=DIFF_LIMIT, ge=0)
    tool_result_max_bytes: int = Field(default=TOOL_RESULT_MAX_BYTES, ge=256)
    read_file_max_lines: int = Field(default=READ_FILE_MAX_LINES, ge=1)
    search_max_matches: int = Field(default=SEARCH_MAX_MATCHES, ge=1)
    extra_refused_read_patterns: tuple[str, ...] = ()

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
        merged = dict(DEFAULT_SEVERITY_MAP)
        merged.update({word.strip().upper(): bucket for word, bucket in value.items()})
        return merged
