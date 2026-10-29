# Every key of the service starts with this text. Another program that shares the Redis cannot clash with it.
KEY_PREFIX = "veil:"
# The first part of the key of each use of the cache.
SETTINGS_FAMILY = "settings"
JIRA_FAMILY = "jira"
REPOS_FAMILY = "repos"
RATE_FAMILY = "rate"
# The format of a stored snapshot. A new format gets a new number, so old entries are never read.
SNAPSHOT_FORMAT = "v1"
# A digest in a key has this many characters. It is enough to tell the texts apart.
DIGEST_LENGTH = 16
# The name of a deployment, for example staging or production. It cannot clash with the key layout.
NAMESPACE_PATTERN = r"^[A-Za-z0-9_.-]{1,40}$"
