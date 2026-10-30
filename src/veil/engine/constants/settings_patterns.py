# A label has no space, quote or backslash. It goes into a search, so it must not change the search.
LABEL = r'^[^\s"\\]+$'
PROJECT_KEY = r"^[A-Z][A-Z0-9_]+$"
BRANCH_PREFIX = r"^[A-Za-z0-9][A-Za-z0-9._/-]*[/-]$"
# Empty, or an https address with no user name and no password in it.
SITE_URL = r"^(https://[^\s/@]+(/[^\s@]*)?)?$"
# The name of an environment variable. It has capital letters, digits and underscores.
ENV_NAME = r"^[A-Z][A-Z0-9_]*$"
