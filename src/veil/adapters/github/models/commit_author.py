from pydantic import BaseModel, ConfigDict

from veil.adapters.github.constants.git import AUTHOR_EMAIL, AUTHOR_NAME


class CommitAuthor(BaseModel):
    """The name and the email on the commits of a run. They hold no secret."""

    model_config = ConfigDict(frozen=True)

    name: str = AUTHOR_NAME
    email: str = AUTHOR_EMAIL
