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
