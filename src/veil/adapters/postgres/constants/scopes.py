# The scope of an org row. A repo row has the scope `repo:` and the name of the repo.
ORG_SCOPE = "org"
REPO_SCOPE_PREFIX = "repo:"
# The session variable that names who writes. The database refuses a write when it is empty.
ACTOR_VARIABLE = "veil.actor"
# The URL of the database for the `alembic` program. A Shell passes an engine instead.
DATABASE_URL_VARIABLE = "VEIL_DATABASE_URL"

# The name of one repo in a scope: owner/name, with no star.
REPO_NAME_PATTERN = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
