from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot
    from veil.engine.models.report.run_report import RunReport
    from veil.shells.service.temporal.constants.names import (
        READ_SETTINGS_ACTIVITY,
        RUN_ENGINE_ACTIVITY,
    )
    from veil.shells.service.temporal.constants.retry import (
        MAX_ATTEMPTS,
        READ_SETTINGS_ATTEMPTS,
        READ_SETTINGS_TIMEOUT_SECONDS,
    )
    from veil.shells.service.temporal.models.run_engine_input import RunEngineInput


@workflow.defn(name="RepoRunWorkflow")
class RepoRunWorkflow:
    """One run of the Engine for one repo. The workflow ID comes from the repo name.

    The workflow reads the settings snapshot once. It passes the snapshot to the activity that runs the Engine.
    So a retry of that activity uses the same settings. The result is the run report. It holds no credential.
    """

    @workflow.run
    async def run(self, repo: str) -> RunReport:
        snapshot = await workflow.execute_activity(
            READ_SETTINGS_ACTIVITY,
            repo,
            result_type=SettingsSnapshot,
            start_to_close_timeout=timedelta(seconds=READ_SETTINGS_TIMEOUT_SECONDS),
            retry_policy=RetryPolicy(maximum_attempts=READ_SETTINGS_ATTEMPTS),
        )
        settings = snapshot.settings_for(repo)
        return await workflow.execute_activity(
            RUN_ENGINE_ACTIVITY,
            RunEngineInput(repo=repo, snapshot=snapshot),
            result_type=RunReport,
            start_to_close_timeout=timedelta(minutes=settings.run_timeout_minutes),
            heartbeat_timeout=timedelta(seconds=settings.heartbeat_seconds),
            retry_policy=RetryPolicy(maximum_attempts=MAX_ATTEMPTS),
        )
