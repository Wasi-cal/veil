API_URL = "https://api.openai.com"
RESPONSES_PATH = "/v1/responses"
# A model call is slow, most of all one that thinks. This is the time-out of one call.
MODEL_CALL_TIMEOUT_SECONDS = 120
# A call that failed with one of these HTTP statuses can work later. A status of 500 or more also can.
RETRYABLE_STATUSES = frozenset({408, 409, 429})
SERVER_ERROR_STATUS = 500
# A reply that failed with one of these codes can work later.
RETRYABLE_ERROR_CODES = frozenset({"server_error", "rate_limit_exceeded"})
# A reply with one of these codes will fail again. A retry cannot help, even when the HTTP status is 429.
PERMANENT_ERROR_CODES = frozenset({"insufficient_quota"})
