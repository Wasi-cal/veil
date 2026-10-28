from veil.engine.constants.outcomes import LEFT_FOR_NEXT_RUN
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.ticket.ticket import Ticket


def leave_for_next_run(tickets: list[Ticket], report: RunReport) -> None:
    """Mark these tickets as left for the next run. Do not touch them in the tracker."""
    for ticket in tickets:
        report.outcomes[ticket.key] = LEFT_FOR_NEXT_RUN
