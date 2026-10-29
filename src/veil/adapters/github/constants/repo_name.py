import re

from veil.adapters.constants.repo_name import REPO_NAME_PATTERN

# A repository name is owner/name. It has no other character that could change a URL.
REPO_NAME = re.compile(REPO_NAME_PATTERN)
