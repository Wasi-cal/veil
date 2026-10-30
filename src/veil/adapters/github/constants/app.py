import re

JWT_ALGORITHM = "RS256"
# GitHub accepts a JWT that lives at most 10 minutes. The start moves back for clock drift.
JWT_LIFETIME_SECONDS = 540
JWT_BACKDATE_SECONDS = 60

# The installation token gets these permissions and no others. It has no workflows permission.
TOKEN_PERMISSIONS = {"contents": "write", "pull_requests": "write"}
# GitHub adds this read permission to every installation token. The check accepts it.
IMPLIED_PERMISSIONS = {"metadata": "read"}

KEY_NOT_VALID = "The GitHub App key is not a valid RSA private key."
NOT_INSTALLED = "The GitHub App is not installed on {repo}."
TOKEN_CHECK_FAILED = "The installation token failed its check: {reason}."
REASON_NO_TOKEN = "the reply holds no token"
REASON_REPOS = "it does not cover this repository alone"
REASON_PERMISSIONS = "it holds permissions that the Action does not need"

# The App itself holds these three permissions and no others. It listens to no events, so its webhook has nothing to send.
APP_PERMISSIONS = {**TOKEN_PERMISSIONS, **IMPLIED_PERMISSIONS}
APP_CHECK_FAILED = "The GitHub App failed its check: {reason}."
REASON_APP_PERMISSIONS = (
    "it holds other permissions than contents, pull requests and metadata"
)
REASON_APP_EVENTS = "it listens to events, but it needs none"
REASON_APP_REPLY = "the reply is not what GitHub sends for an App"
# GitHub gives a bot user the name of the App with this ending. Its commit email holds the user ID.
BOT_SUFFIX = "[bot]"
BOT_EMAIL = "{user_id}+{slug}[bot]@users.noreply.github.com"
# The login of an organization or a user.
ACCOUNT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}")
# One list of repos is at most this many pages of 100. A list that is longer is a fault.
LIST_PAGE_LIMIT = 50
REASON_LIST_PERMISSIONS = "it holds other permissions than metadata"
LIST_REFUSED = "The list of repos failed its check: {reason}."
ACCOUNT_REFUSED = "Refused the account name."
APP_SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}")
REASON_LIST_TOO_LONG = "the list has more pages than the limit"
