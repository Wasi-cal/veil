from typing import Protocol, runtime_checkable

from veil.engine.interfaces.workspace import Workspace


@runtime_checkable
class RepoProvider(Protocol):
    def open_workspace(self, repo: str) -> Workspace: ...
    def open_draft_pr(self, repo: str, branch: str, title: str, body: str) -> str: ...
