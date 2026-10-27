from pydantic import BaseModel, ConfigDict


class ListDirArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = "."
