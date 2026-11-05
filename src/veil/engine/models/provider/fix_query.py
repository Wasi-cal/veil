from pydantic import BaseModel, ConfigDict


class FixQuery(BaseModel):
    """The question that the Engine asks the repo provider: is there already a Fix for this ticket?

    A Fix PR carries the label `veil-fix` and has a section for the ticket key. A Fix PR from before that change carries the issue label.
    """

    model_config = ConfigDict(frozen=True)

    repo: str
    ticket_key: str
    issue_label: str
    source_branch: str
    branch_prefix: str
