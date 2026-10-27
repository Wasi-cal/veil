from pydantic import BaseModel, ConfigDict

from veil.engine.interfaces import ModelClient, RepoProvider, Tracker
from veil.engine.models.settings import Settings


class Context(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    settings: Settings
    tracker: Tracker
    repo_provider: RepoProvider
    model_client: ModelClient
