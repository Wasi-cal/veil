from pathlib import Path

from veil.engine.models.report.run_report import RunReport
from veil.shells.github_action.constants.messages import (
    SUMMARY_PRS,
    SUMMARY_SKIPPED,
    SUMMARY_TICKETS,
    SUMMARY_TITLE,
    SUMMARY_TOKENS,
)


def write_summary(report: RunReport, path: Path | None) -> None:
    """Append the run report to the step summary of the runner. Do nothing without a file."""
    if path is None:
        return
    lines = [SUMMARY_TITLE, "", SUMMARY_TOKENS.format(count=report.tokens_used), ""]
    if report.pull_requests:
        lines += [SUMMARY_PRS, *(f"- {url}" for url in report.pull_requests), ""]
    if report.outcomes:
        lines += [
            SUMMARY_TICKETS,
            "| Ticket | Outcome |",
            "| --- | --- |",
            *(f"| {key} | {outcome} |" for key, outcome in report.outcomes.items()),
            "",
        ]
    if report.skipped:
        lines += [
            SUMMARY_SKIPPED,
            *(
                f"- {reason}: {', '.join(keys)}"
                for reason, keys in report.skipped.items()
            ),
            "",
        ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
