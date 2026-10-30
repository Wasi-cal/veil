from pydantic import BaseModel, ConfigDict

from veil.adapters.github.constants.app import BOT_EMAIL, BOT_SUFFIX
from veil.adapters.github.models.commit_author import CommitAuthor


class GitHubApp(BaseModel):
    """The GitHub App of the service. The adapter checks its permissions and events before it returns it."""

    model_config = ConfigDict(frozen=True)

    slug: str
    bot_user_id: int

    @property
    def commit_author(self) -> CommitAuthor:
        """The bot of the App. The email holds the user ID, so it never changes and GitHub shows the App on a commit."""
        return CommitAuthor(
            name=f"{self.slug}{BOT_SUFFIX}",
            email=BOT_EMAIL.format(user_id=self.bot_user_id, slug=self.slug),
        )
