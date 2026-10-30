from collections.abc import Callable

from temporalio import activity
from temporalio.exceptions import ApplicationError

from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot
from veil.engine.context import Context
from veil.engine.models.report.run_report import RunReport
from veil.engine.run import run as run_engine
from veil.shells.service.errors.run_failed import RunFailed
from veil.shells.service.models.service_dependencies import ServiceDependencies
from veil.shells.service.run_repo import run_repo
from veil.shells.service.temporal.constants.names import (
    READ_SETTINGS_ACTIVITY,
    RUN_ENGINE_ACTIVITY,
)
from veil.shells.service.temporal.models.run_engine_input import RunEngineInput


class EngineActivities:
    """The two activities of the service. A worker builds one object and registers its methods."""

    def __init__(
        self,
        dependencies: ServiceDependencies,
        run: Callable[[Context], RunReport] = run_engine,
    ) -> None:
        self._deps = dependencies
        self._run = run

    @activity.defn(name=READ_SETTINGS_ACTIVITY)
    def read_settings(self, repo: str) -> SettingsSnapshot:
        """Read the settings snapshot for one repo. The workflow keeps it, so every retry sees the same values."""
        return self._deps.settings_source.read_snapshot([repo])

    @activity.defn(name=RUN_ENGINE_ACTIVITY)
    def run_engine(self, run_input: RunEngineInput) -> RunReport:
        """Run the Engine once for one repo. Send a heartbeat with the tokens used after each step.

        A retry reads the tokens of the last heartbeat. `run_repo` lowers the token ceiling by that number.
        A run failure becomes a Temporal error that says if Temporal may retry.
        """
        try:
            return run_repo(
                self._deps,
                run_input.repo,
                run_input.snapshot,
                prior_tokens=_tokens_in_last_heartbeat(),
                progress=activity.heartbeat,
                run=self._run,
            )
        except RunFailed as failure:
            raise ApplicationError(
                str(failure),
                type=failure.error_type,
                non_retryable=not failure.retryable,
            ) from None


def _tokens_in_last_heartbeat() -> int:
    details = activity.info().heartbeat_details
    return int(details[0]) if details and isinstance(details[0], int) else 0
