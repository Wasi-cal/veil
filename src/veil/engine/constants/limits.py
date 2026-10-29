STEP_CAP = 25
DIFF_LIMIT = 200
READ_FILE_MAX_LINES = 300
SEARCH_MAX_MATCHES = 50
TOOL_RESULT_MAX_BYTES = 8 * 1024
TOKEN_CEILING = 100_000
EXPLANATION_MAX_SENTENCES = 3
SHARED_PR_MAX = 10
MIN_SECRET_LENGTH = 8
MIN_TOOL_RESULT_MAX_BYTES = 256
# One attempt with the cheap model, then one with the strong model.
MAX_ATTEMPTS = 2
# The attempt number from which the strong model runs.
STRONG_MODEL_ATTEMPT = 2
# A low rate. The shared counter in Redis enforces it, not the Engine.
MODEL_CALLS_PER_MINUTE = 20
