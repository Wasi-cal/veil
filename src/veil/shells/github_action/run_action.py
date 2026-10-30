import os
import sys
from collections.abc import Callable, Mapping
from typing import TextIO

from veil.adapters.constants.settings_file import REPO_SETTINGS_PATH
from veil.adapters.github.app_token import GitHubAppTokenSource
from veil.adapters.github.token_source import TokenSource
from veil.adapters.jira.models.jira_settings import JiraSettings
from veil.adapters.yaml_settings import load_settings_file
from veil.engine.config.resolve import resolve_settings
from veil.engine.context import Context
from veil.engine.errors.model_client_error import ModelClientError
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.settings_error import SettingsError
from veil.engine.errors.tracker_error import TrackerError
from veil.engine.models.report.run_report import RunReport
from veil.engine.run import run as run_engine
from veil.engine.secrets.redact import redact
from veil.shells.github_action.constants.messages import (
    UNEXPECTED_ERROR,
)
from veil.shells.github_action.credentials import (
    read_app_credentials,
    read_credentials,
)
from veil.shells.github_action.environment import read_run_environment
from veil.shells.github_action.errors.action_failure import ActionFailure
from veil.shells.github_action.masking import mask_values
from veil.shells.github_action.summary import write_summary
from veil.shells.github_action.triggers import skip_reason
from veil.shells.shared.context_builder import build_context
from veil.shells.shared.models.service_urls import ServiceUrls


def run_action(
    environ: Mapping[str, str],
    *,
    urls: ServiceUrls | None = None,
    token_source: TokenSource | None = None,
    run: Callable[[Context], RunReport] = run_engine,
    out: TextIO | None = None,
) -> int:
    """Run the Engine once for the repo of the workflow. Return the exit code of the Action.

    Every check that needs no token comes first. Then the Action mints the GitHub token.
    It masks each credential in the log before it uses the value. A failure prints one error line and returns 1.
    A failure never touches a ticket. The message hides the credential values of the run.
    """
    stream: TextIO = out or sys.stdout
    urls = urls or ServiceUrls()
    known: list[str] = []
    try:
        return _run(environ, urls, token_source, run, stream, known)
    except Exception as failure:  # noqa: BLE001 - the last resort. A crash must still print a redacted line
        message = (
            str(failure)
            if _is_expected(failure)
            else f"{UNEXPECTED_ERROR} {type(failure).__name__}: {failure}"
        )
        print(f"::error::{redact(message, tuple(known))}", file=stream, flush=True)
        return 1


def _is_expected(failure: Exception) -> bool:
    return isinstance(
        failure,
        ActionFailure
        | ModelClientError
        | RepoProviderError
        | SettingsError
        | TrackerError,
    )


def _run(
    environ: Mapping[str, str],
    urls: ServiceUrls,
    token_source: TokenSource | None,
    run: Callable[[Context], RunReport],
    out: TextIO,
    known: list[str],
) -> int:
    env = read_run_environment(environ)
    settings = resolve_settings(
        repo=load_settings_file(env.workspace / REPO_SETTINGS_PATH)
    )
    reason = skip_reason(env.event, settings)
    if reason:
        print(f"::notice::{reason}", file=out, flush=True)
        return 0
    jira = JiraSettings.from_settings(settings)
    credentials = read_credentials(environ, settings)
    known += [
        credentials.jira_token.get_secret_value(),
        credentials.openai_key.get_secret_value(),
    ]
    if token_source is None:
        app = read_app_credentials(environ)
        known.append(app.private_key.get_secret_value())
        token_source = GitHubAppTokenSource(
            app.app_id, app.private_key, base_url=urls.github_api_url
        )
    mask_values(tuple(known), out)
    source = token_source
    token = source.mint(env.repo)
    known.append(token.get_secret_value())
    mask_values((token.get_secret_value(),), out)

    context, provider = build_context(
        settings, jira, credentials, token, urls, env.repo
    )
    try:
        report = run(context)
    finally:
        provider.close()
    write_summary(report.redacted(context.redact), env.summary_file)
    return 0


def main() -> None:
    """The entry point of the container. The exit code tells the runner if the run failed."""
    sys.exit(run_action(os.environ))
