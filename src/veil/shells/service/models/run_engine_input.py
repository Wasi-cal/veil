from pydantic import BaseModel, ConfigDict

from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot


class RunEngineInput(BaseModel):
    """The input of the activity that runs the Engine. It holds no credential.

    The snapshot is plain data. A retry of the activity reads the same snapshot, so it uses the same values.
    """

    model_config = ConfigDict(frozen=True)

    repo: str
    snapshot: SettingsSnapshot
