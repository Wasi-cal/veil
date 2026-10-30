from veil.adapters.github.app_token import GitHubAppTokenSource
from veil.adapters.redis.repo_list_cache import RepoListCache
from veil.engine.models.config.settings import Settings


def eligible_repos(
    source: GitHubAppTokenSource,
    owner: str,
    settings: Settings,
    cache: RepoListCache | None = None,
) -> list[str]:
    """The repos that the service may run. They are the repos of the installation, narrowed by the org settings.

    A repo must be in the installation. If `repos_allow` is not empty, the repo must be in it too.
    A repo in `repos_deny` never runs. The names match whatever the case, as GitHub does.
    The list of the installation comes from the cache when the cache holds it.
    """
    installation = source.installation_id(owner)

    def load() -> list[str]:
        return source.list_repos(installation)

    installed = cache.get_or_load(installation, load) if cache else load()
    allow = {name.casefold() for name in settings.repos_allow}
    deny = {name.casefold() for name in settings.repos_deny}
    return [
        repo
        for repo in installed
        if (not allow or repo.casefold() in allow) and repo.casefold() not in deny
    ]
