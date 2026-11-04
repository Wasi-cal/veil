from collections.abc import Callable

from pydantic import BaseModel, Field

from veil.engine.models.report.ticket_usage import TicketUsage


class RunReport(BaseModel):
    pull_requests: list[str] = Field(default_factory=list)
    outcomes: dict[str, str] = Field(default_factory=dict)
    reasons: dict[str, str] = Field(default_factory=dict)
    # The tickets whose Fix may break something, with the reason of each.
    breaking: dict[str, str] = Field(default_factory=dict)
    usage: dict[str, TicketUsage] = Field(default_factory=dict)
    skipped: dict[str, list[str]] = Field(default_factory=dict)
    tokens_used: int = 0
    stopped: str | None = None

    def redacted(self, redact: Callable[[str], str]) -> "RunReport":
        """Return a copy of the report with `redact` applied to each text."""
        return RunReport(
            pull_requests=[redact(url) for url in self.pull_requests],
            outcomes={redact(key): outcome for key, outcome in self.outcomes.items()},
            reasons={redact(key): redact(text) for key, text in self.reasons.items()},
            breaking={redact(key): redact(text) for key, text in self.breaking.items()},
            usage={redact(key): usage for key, usage in self.usage.items()},
            skipped={
                reason: [redact(key) for key in keys]
                for reason, keys in self.skipped.items()
            },
            tokens_used=self.tokens_used,
            stopped=self.stopped,
        )
