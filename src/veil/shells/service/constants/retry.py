# A tracker call that failed with one of these HTTP statuses can work later. A status of 500 or more also can.
TRACKER_RETRY_STATUSES = frozenset({408, 429})
SERVER_ERROR_STATUS = 500
