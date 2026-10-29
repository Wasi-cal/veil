from pydantic import BaseModel, ConfigDict


class ApiFunctionCall(BaseModel):
    """One call of a function in a reply of the API. The arguments are the JSON text that the model wrote."""

    model_config = ConfigDict(frozen=True)

    call_id: str
    name: str
    arguments: str
