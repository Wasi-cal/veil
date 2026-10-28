import re

# A repository name is owner/name. It has no other character that could change a URL.
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
