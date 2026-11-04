from pathlib import Path

from veil.engine.models.report.run_report import RunReport
from veil.shells.github_action.constants.messages import (
    SUMMARY_BREAKING,
    SUMMARY_ESCALATED,
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
    usages = report.usage.values()
    totals = SUMMARY_TOKENS.format(
        count=report.tokens_used,
        input=sum(usage.input for usage in usages),
        output=sum(usage.output for usage in usages),
    )
    lines = [SUMMARY_TITLE, "", totals, ""]
    if report.pull_requests:
        lines += [SUMMARY_PRS, *(f"- {url}" for url in report.pull_requests), ""]
    if report.outcomes:
        lines += [
            SUMMARY_TICKETS,
            "| Ticket | Outcome | Input | Output | Total | Escalated | Reason |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
            *(
                _ticket_row(report, key, outcome)
                for key, outcome in report.outcomes.items()
            ),
            "",
        ]
    if report.breaking:
        lines += [
            SUMMARY_BREAKING,
            "| Ticket | Reason |",
            "| --- | --- |",
            *(f"| {key} | {_cell(text)} |" for key, text in report.breaking.items()),
            "",
        ]
    escalated = [(key, usage) for key, usage in report.usage.items() if usage.escalated]
    if escalated:
        lines += [
            SUMMARY_ESCALATED,
            "| Ticket | Model | Input | Output | Total |",
            "| --- | --- | ---: | ---: | ---: |",
            *(
                f"| {key} | {_cell(model)} | {t.input} | {t.output} | {t.total} |"
                for key, usage in escalated
                for model, t in usage.by_model.items()
            ),
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


def _cell(text: str) -> str:
    """Make text safe for one cell of a Markdown table: one line, and no bare pipe."""
    return " ".join(text.split()).replace("|", "\\|")


def _ticket_row(report: RunReport, key: str, outcome: str) -> str:
    usage = report.usage.get(key)
    counts = f"{usage.input} | {usage.output} | {usage.total}" if usage else " |  | "
    escalated = "yes" if usage and usage.escalated else "no" if usage else ""
    return f"| {key} | {outcome} | {counts} | {escalated} | {_cell(report.reasons.get(key, ''))} |"
