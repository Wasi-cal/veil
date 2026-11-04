from pathlib import Path

from pydantic import BaseModel, ConfigDict


class RunEnvironment(BaseModel):
    """What the runner tells the Action about this run. None of it is secret."""

    model_config = ConfigDict(frozen=True)

    repo: str
    workspace: Path
    event: str
    event_path: Path | None
    ref_name: str | None
    summary_file: Path | None
