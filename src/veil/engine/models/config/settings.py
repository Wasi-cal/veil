from pydantic import BaseModel, ConfigDict, Field

from veil.engine.constants.limits import (
    DIFF_LIMIT,
    READ_FILE_MAX_LINES,
    SEARCH_MAX_MATCHES,
    STEP_CAP,
    TOKEN_CEILING,
    TOOL_RESULT_MAX_BYTES,
)
from veil.engine.constants.models import CHEAP_MODEL, STRONG_MODEL


class Settings(BaseModel):
    """The defaults are in code. The caller can give other values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cheap_model: str = Field(default=CHEAP_MODEL, min_length=1)
    strong_model: str = Field(default=STRONG_MODEL, min_length=1)
    token_ceiling: int = Field(default=TOKEN_CEILING, ge=1)
    step_cap: int = Field(default=STEP_CAP, ge=1)
    diff_limit: int = Field(default=DIFF_LIMIT, ge=0)
    tool_result_max_bytes: int = Field(default=TOOL_RESULT_MAX_BYTES, ge=256)
    read_file_max_lines: int = Field(default=READ_FILE_MAX_LINES, ge=1)
    search_max_matches: int = Field(default=SEARCH_MAX_MATCHES, ge=1)
    extra_refused_read_patterns: tuple[str, ...] = ()
