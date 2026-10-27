from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class Ticket(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    repo: str
    file: str
    line: int
    severity: str
    finding: str


class ToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ModelReply(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_calls: list[ToolCall]
    tokens: int = 0


@runtime_checkable
class Tracker(Protocol):
    def open_tickets(self) -> list[Ticket]: ...
    def add_comment(self, key: str, text: str) -> None: ...
    def set_status(self, key: str, status: str) -> None: ...


@runtime_checkable
class Workspace(Protocol):
    def read_file(self, path: str) -> str: ...
    def edit_file(self, path: str, old: str, new: str) -> None: ...
    def commit(self, branch: str, message: str) -> None: ...


@runtime_checkable
class RepoProvider(Protocol):
    def open_workspace(self, repo: str) -> Workspace: ...
    def open_draft_pr(self, repo: str, branch: str, title: str, body: str) -> str: ...


@runtime_checkable
class ModelClient(Protocol):
    def next(self, messages: list[dict]) -> ModelReply: ...
