from collections.abc import Callable

from veil.adapters.jira.models.jira_settings import JiraSettings
from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot
from veil.engine.context import Context
from veil.engine.models.report.run_report import RunReport
from veil.engine.run import run as run_engine
from veil.engine.secrets.redact import redact
from veil.shells.service.classify_failure import classify_failure
from veil.shells.service.models.service_dependencies import ServiceDependencies
from veil.shells.shared.context_builder import build_context


def run_repo(
    dependencies: ServiceDependencies,
    repo: str,
    snapshot: SettingsSnapshot,
    prior_tokens: int = 0,
    progress: Callable[[int], None] | None = None,
    run: Callable[[Context], RunReport] = run_engine,
) -> RunReport:
    """Run the Engine once for one repo. This is the work of the service, with no runner in it.

    `prior_tokens` is what an earlier attempt of the same run used. It lowers the token ceiling.
    `progress` gets the tokens used so far, with the prior tokens added. A runner uses it for a heartbeat.
    The function mints the token and keeps it here. It closes the checkouts at the end.
    Raise RunFailed for any error. The message is redacted. The result is the run report.
    """
    settings = snapshot.settings_for(repo)
    settings = settings.model_copy(
        update={"token_ceiling": max(0, settings.token_ceiling - prior_tokens)}
    )
    secrets = [
        dependencies.credentials.jira_token.get_secret_value(),
        dependencies.credentials.openai_key.get_secret_value(),
    ]
    provider = None
    try:
        token = dependencies.token_source.mint(repo)
        secrets.append(token.get_secret_value())
        context, provider = build_context(
            settings,
            JiraSettings.from_settings(settings),
            dependencies.credentials,
            token,
            dependencies.urls,
            repo,
            metadata_cache=dependencies.metadata_cache,
            temp_root=dependencies.checkout_root,
            progress=(lambda used: progress(prior_tokens + used)) if progress else None,
            author=dependencies.author,
        )
        report = run(context)
    except Exception as failure:  # noqa: BLE001 - one error type with a redacted message leaves this function
        raise classify_failure(
            failure, lambda text: redact(text, tuple(secrets))
        ) from None
    finally:
        if provider is not None:
            provider.close()
    return report.model_copy(update={"tokens_used": report.tokens_used + prior_tokens})
