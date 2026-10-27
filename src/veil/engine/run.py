from veil.engine.context import Context
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.fix.attempt import attempt
from veil.engine.fix.failures import record_failed_fix
from veil.engine.models.report.run_report import RunReport


def run(context: Context) -> RunReport:
    """Fix the open Gozu Tickets. Return the report of the run."""
    report = RunReport()
    for ticket in context.tracker.open_tickets():
        try:
            attempt(context, ticket, report)
        except FailedFix as failed:
            record_failed_fix(context, ticket, failed, report)
    return report
