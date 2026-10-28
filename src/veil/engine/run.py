from veil.engine.context import Context
from veil.engine.eligibility.select import distinct, select_eligible
from veil.engine.errors.budget_exhausted import BudgetExhausted
from veil.engine.fix.failures import leave_for_next_run
from veil.engine.fix.group import fix_group
from veil.engine.grouping.plan import plan_groups
from veil.engine.models.report.run_report import RunReport


def run(context: Context) -> RunReport:
    """Fix the eligible Gozu Tickets. Return the report of the run.

    The Engine skips a ticket that has a fix already. It puts the rest into groups. Each group gets one Fix PR.
    At the token ceiling the run stops. The Fixes that passed are published. The other tickets stay untouched for the next run.
    """
    report = RunReport()
    tickets = select_eligible(
        distinct(context.tracker.open_tickets()),
        context.repo_provider,
        context.settings,
        report,
    )
    plan = plan_groups(tickets, context.settings)
    leave_for_next_run(list(plan.left_for_next_run), report)
    planned = [ticket for group in plan.groups for ticket in group.tickets]
    for group in plan.groups:
        try:
            fix_group(context, group, report)
        except BudgetExhausted:
            left = [t for t in planned if t.key not in report.outcomes]
            leave_for_next_run(left, report)
            break
    return report
