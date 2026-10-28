from veil.engine.errors.budget_exhausted import BudgetExhausted
from veil.engine.models.config.settings import Settings
from veil.engine.models.report.run_report import RunReport


def ensure_budget(report: RunReport, settings: Settings) -> None:
    """Raise BudgetExhausted if the run used its token ceiling."""
    if report.tokens_used >= settings.token_ceiling:
        raise BudgetExhausted
