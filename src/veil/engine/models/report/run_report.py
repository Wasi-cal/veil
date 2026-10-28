from collections.abc import Callable

from pydantic import BaseModel, Field


class RunReport(BaseModel):
    pull_requests: list[str] = Field(default_factory=list)
    outcomes: dict[str, str] = Field(default_factory=dict)
    skipped: dict[str, list[str]] = Field(default_factory=dict)
    tokens_used: int = 0

    def redacted(self, redact: Callable[[str], str]) -> "RunReport":
        """Return a copy of the report with `redact` applied to each text."""
        return RunReport(
            pull_requests=[redact(url) for url in self.pull_requests],
            outcomes={redact(key): outcome for key, outcome in self.outcomes.items()},
            skipped={
                reason: [redact(key) for key in keys]
                for reason, keys in self.skipped.items()
            },
            tokens_used=self.tokens_used,
        )
