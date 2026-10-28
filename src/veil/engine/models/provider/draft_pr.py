from pydantic import BaseModel, ConfigDict


class DraftPr(BaseModel):
    """What the repo provider needs to open a draft Fix PR.

    The head is the gozu/fix-* branch of the Fix. The base is the branch of the Source PR. The Fix PR targets the base and not the default branch.
    """

    model_config = ConfigDict(frozen=True)

    repo: str
    head: str
    base: str
    title: str
    body: str
    labels: tuple[str, ...]
