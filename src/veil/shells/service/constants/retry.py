# One activity runs the Engine for one repo. It has at most this many attempts.
MAX_ATTEMPTS = 2
# A tracker call that failed with one of these HTTP statuses can work later. A status of 500 or more also can.
TRACKER_RETRY_STATUSES = frozenset({408, 429})
SERVER_ERROR_STATUS = 500
# The settings snapshot is a small read from PostgreSQL or Redis.
READ_SETTINGS_TIMEOUT_SECONDS = 30
READ_SETTINGS_ATTEMPTS = 3
