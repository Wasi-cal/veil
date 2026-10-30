# The client tries one failed call again at most this many times. A call that can work later is one with retryable set.
MODEL_CALL_RETRIES = 2
# The pause before the first new try. Each new try waits twice as long, up to the cap.
RETRY_BASE_DELAY_SECONDS = 1.0
RETRY_MAX_DELAY_SECONDS = 8.0
