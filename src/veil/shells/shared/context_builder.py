from collections.abc import Callable
from pathlib import Path

from pydantic import SecretStr

from veil.adapters.github.http_api import HttpGitHubApi
from veil.adapters.github.provider import GitHubRepoProvider
from veil.adapters.jira.gateway import resolve_api_base
from veil.adapters.jira.metadata_cache import MetadataCache
from veil.adapters.jira.models.jira_credentials import JiraCredentials
from veil.adapters.jira.models.jira_settings import JiraSettings
from veil.adapters.jira.tracker import JiraTracker
from veil.adapters.openai.client import OpenAIModelClient
from veil.adapters.openai.http_api import HttpOpenAIApi
from veil.engine.context import Context
from veil.engine.models.config.settings import Settings
from veil.shells.shared.models.run_credentials import RunCredentials
from veil.shells.shared.models.service_urls import ServiceUrls
from veil.shells.shared.repo_scoped_tracker import RepoScopedTracker


def build_context(
    settings: Settings,
    jira: JiraSettings,
    credentials: RunCredentials,
    github_token: SecretStr,
    urls: ServiceUrls,
    repo: str,
    metadata_cache: MetadataCache | None = None,
    temp_root: Path | None = None,
    progress: Callable[[int], None] | None = None,
) -> tuple[Context, GitHubRepoProvider]:
    """Build the Engine context from the real adapters. Return the repo provider too, so the caller can close it.

    The GitHub token goes to the repo provider and its API only. The Jira token goes to the tracker only.
    The OpenAI key goes to the model client only. A Shell may give a Jira metadata cache, a root for the checkouts and a progress callback. The tracker shows the Engine the tickets of this repo only.
    """
    provider = GitHubRepoProvider(
        token=github_token,
        api=HttpGitHubApi(github_token, base_url=urls.github_api_url),
        remote_url=lambda repo: f"{urls.git_url}/{repo}.git",
        branch_prefix=settings.branch_prefix,
        temp_root=temp_root,
    )
    try:
        jira_tracker = JiraTracker(
            jira,
            JiraCredentials(
                email=credentials.jira_email, api_token=credentials.jira_token
            ),
            api_base=urls.jira_api_base or resolve_api_base(jira.site_url),
            metadata_cache=metadata_cache,
        )
        context = Context(
            settings=settings,
            tracker=RepoScopedTracker(jira_tracker, repo),
            repo_provider=provider,
            model_client=OpenAIModelClient(
                HttpOpenAIApi(credentials.openai_key, base_url=urls.openai_api_url)
            ),
            credentials=(github_token, credentials.jira_token, credentials.openai_key),
            progress=progress,
        )
    except BaseException:
        provider.close()
        raise
    return context, provider
