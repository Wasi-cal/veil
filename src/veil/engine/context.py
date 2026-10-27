from pydantic import BaseModel, ConfigDict

from veil.engine.interfaces.model_client import ModelClient
from veil.engine.interfaces.repo_provider import RepoProvider
from veil.engine.interfaces.tracker import Tracker
from veil.engine.models.config.settings import Settings


class Context(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    settings: Settings
    tracker: Tracker
    repo_provider: RepoProvider
    model_client: ModelClient
