import re

# A Jira key is a project key, a dash and a number. It has no character that could change a URL.
ISSUE_KEY = re.compile(r"^[A-Z][A-Z0-9_]+-[0-9]+$")
# A label has no space, quote or backslash. Jira labels cannot hold a space.
SAFE_LABEL = re.compile(r'^[^\s"\\]+$')
PROJECT_KEY = re.compile(r"^[A-Z][A-Z0-9_]+$")
