from typing import Protocol, runtime_checkable

from veil.engine.models.llm.model_reply import ModelReply


@runtime_checkable
class ModelClient(Protocol):
    def next(self, messages: list[dict], model: str) -> ModelReply: ...
