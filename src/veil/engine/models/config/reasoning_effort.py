from typing import Literal

# The levels that the OpenAI Responses API takes for the reasoning effort of a model.
# A model may not take every level. The API refuses a level that the model does not take.
ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh", "max"]
