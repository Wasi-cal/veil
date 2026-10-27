from pydantic import BaseModel, ConfigDict


class EditFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    old: str
    new: str
