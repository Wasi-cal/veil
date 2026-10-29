# The reader sees one point in time. A write after the first read does not show in the snapshot.
SNAPSHOT_ISOLATION_LEVEL = "REPEATABLE READ"

# The names of the first and the last revision of the migrations, for Alembic.
BASE_REVISION = "base"
HEAD_REVISION = "head"

# Two deployments that migrate at the same time take turns with this lock of the database.
MIGRATION_LOCK_KEY = 7_166_001
