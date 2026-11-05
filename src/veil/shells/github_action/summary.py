from pathlib import Path

from veil.engine.fix.cost import cost_by_model, cost_of
from veil.engine.models.report.model_price import ModelPrice
from veil.engine.models.report.run_report import RunReport
from veil.shells.github_action.constants.messages import (
    SUMMARY_BREAKING,
    SUMMARY_COST,
    SUMMARY_ESCALATED,
    SUMMARY_NO_PRICE,
    SUMMARY_PRS,
    SUMMARY_SKIPPED,
    SUMMARY_TICKETS,
    SUMMARY_TITLE,
    SUMMARY_TOKENS,
)


def write_summary(
    report: RunReport, path: Path | None, prices: dict[str, ModelPrice] | None = None
) -> None:
    """Append the run report to the step summary of the runner. Do nothing without a file.

    The prices give the cost of the tokens. Without prices, no cost shows.
    """
    prices = prices or {}
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
            "| Ticket | Model | Input | Output | Total | Input cost | Output cost |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            *(
                f"| {key} | {_cell(model)} | {t.input} | {t.output} | {t.total} | "
                f"{_usd(cost_of(t, prices.get(model)).input_cost)} | "
                f"{_usd(cost_of(t, prices.get(model)).output_cost)} |"
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
    lines += _cost_lines(report, prices)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _cost_lines(report: RunReport, prices: dict[str, ModelPrice]) -> list[str]:
    """The cost of each model and the total. This is the last part of the summary."""
    costs = cost_by_model(report.usage.values(), prices)
    if not costs:
        return []
    rows = [
        f"| {_cell(model)} | {c.uncached} | {c.cached} | {c.output} | "
        f"{_usd(c.input_cost)} | {_usd(c.output_cost)} | {_usd(c.total_cost)} |"
        for model, c in costs.items()
    ]
    priced = [c for c in costs.values() if c.total_cost is not None]
    input_cost = sum(c.input_cost for c in priced)
    output_cost = sum(c.output_cost for c in priced)
    rows.append(
        f"| **Total** | {sum(c.uncached for c in costs.values())} | {sum(c.cached for c in costs.values())} | "
        f"{sum(c.output for c in costs.values())} | {_usd(input_cost)} | {_usd(output_cost)} | {_usd(input_cost + output_cost)} |"
    )
    unpriced = [model for model, c in costs.items() if c.total_cost is None]
    lines = [
        SUMMARY_COST,
        "| Model | Input (not cached) | Input (cached) | Output | Input cost | Output cost | Total cost |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *rows,
        "",
    ]
    if unpriced:
        lines += [
            SUMMARY_NO_PRICE.format(
                models=", ".join(f"`{_cell(m)}`" for m in unpriced)
            ),
            "",
        ]
    return lines


def _usd(amount: float | None) -> str:
    return "n/a" if amount is None else f"${amount:.4f}"


def _cell(text: str) -> str:
    """Make text safe for one cell of a Markdown table: one line, and no bare pipe."""
    return " ".join(text.split()).replace("|", "\\|")


def _ticket_row(report: RunReport, key: str, outcome: str) -> str:
    usage = report.usage.get(key)
    counts = f"{usage.input} | {usage.output} | {usage.total}" if usage else " |  | "
    escalated = "yes" if usage and usage.escalated else "no" if usage else ""
    return f"| {key} | {outcome} | {counts} | {escalated} | {_cell(report.reasons.get(key, ''))} |"
