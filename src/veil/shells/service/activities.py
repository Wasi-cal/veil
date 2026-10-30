from collections.abc import Callable

from temporalio import activity

from veil.adapters.jira.models.jira_settings import JiraSettings
from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot
from veil.engine.context import Context
from veil.engine.models.report.run_report import RunReport
from veil.engine.run import run as run_engine
from veil.engine.secrets.redact import redact
from veil.shells.service.constants.names import (
    READ_SETTINGS_ACTIVITY,
    RUN_ENGINE_ACTIVITY,
)
from veil.shells.service.error_mapping import to_application_error
from veil.shells.service.models.run_engine_input import RunEngineInput
from veil.shells.service.models.service_dependencies import ServiceDependencies
from veil.shells.shared.context_builder import build_context


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

        A retry reads the tokens of the last heartbeat. It lowers the token ceiling by that number.
        This function mints the token and keeps it. The result is the run report.
        """
        repo = run_input.repo
        prior = _tokens_in_last_heartbeat()
        settings = run_input.snapshot.settings_for(repo)
        settings = settings.model_copy(
            update={"token_ceiling": max(0, settings.token_ceiling - prior)}
        )
        secrets = [
            self._deps.credentials.jira_token.get_secret_value(),
            self._deps.credentials.openai_key.get_secret_value(),
        ]
        provider = None
        try:
            token = self._deps.token_source.mint(repo)
            secrets.append(token.get_secret_value())
            context, provider = build_context(
                settings,
                JiraSettings.from_settings(settings),
                self._deps.credentials,
                token,
                self._deps.urls,
                repo,
                metadata_cache=self._deps.metadata_cache,
                temp_root=self._deps.checkout_root,
                progress=lambda used: activity.heartbeat(prior + used),
            )
            report = self._run(context)
        except Exception as failure:  # noqa: BLE001 - Temporal needs one error type with a redacted message
            raise to_application_error(
                failure, lambda text: redact(text, tuple(secrets))
            ) from None
        finally:
            if provider is not None:
                provider.close()
        return report.model_copy(update={"tokens_used": report.tokens_used + prior})


def _tokens_in_last_heartbeat() -> int:
    details = activity.info().heartbeat_details
    return int(details[0]) if details and isinstance(details[0], int) else 0
