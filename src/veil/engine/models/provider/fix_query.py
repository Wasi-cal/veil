from pydantic import BaseModel, ConfigDict


class FixQuery(BaseModel):
    """The question that the Engine asks the repo provider: is there already a Fix for this ticket?"""

    model_config = ConfigDict(frozen=True)

    repo: str
    issue_label: str
    source_branch: str
    branch_prefix: str
