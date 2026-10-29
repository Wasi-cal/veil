from pydantic import BaseModel, ConfigDict

from veil.adapters.github.constants.http import API_URL as GITHUB_API_URL
from veil.adapters.openai.constants.http import API_URL as OPENAI_API_URL
from veil.shells.github_action.constants.urls import GIT_URL


class ServiceUrls(BaseModel):
    """The addresses of the services. The defaults are the real services. A test points them at stubs.

    A Jira address of None means that the Action asks the Jira site for its gateway address.
    """

    model_config = ConfigDict(frozen=True)

    github_api_url: str = GITHUB_API_URL
    git_url: str = GIT_URL
    openai_api_url: str = OPENAI_API_URL
    jira_api_base: str | None = None
