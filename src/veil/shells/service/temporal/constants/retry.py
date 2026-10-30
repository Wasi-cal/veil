# One activity runs the Engine for one repo. It has at most this many attempts.
MAX_ATTEMPTS = 2
# The settings snapshot is a small read from PostgreSQL or Redis.
READ_SETTINGS_TIMEOUT_SECONDS = 30
READ_SETTINGS_ATTEMPTS = 3
