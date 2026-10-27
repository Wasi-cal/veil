from pydantic import BaseModel, ConfigDict, Field

from veil.engine.constants.limits import (
    DIFF_LIMIT,
    READ_FILE_MAX_LINES,
    SEARCH_MAX_MATCHES,
    STEP_CAP,
    TOOL_RESULT_MAX_BYTES,
)


class Settings(BaseModel):
    """Defaults live in code. Callers pass their own values in."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_cap: int = Field(default=STEP_CAP, ge=1)
    diff_limit: int = Field(default=DIFF_LIMIT, ge=0)
    tool_result_max_bytes: int = Field(default=TOOL_RESULT_MAX_BYTES, ge=256)
    read_file_max_lines: int = Field(default=READ_FILE_MAX_LINES, ge=1)
    search_max_matches: int = Field(default=SEARCH_MAX_MATCHES, ge=1)
    extra_refused_read_patterns: tuple[str, ...] = ()
