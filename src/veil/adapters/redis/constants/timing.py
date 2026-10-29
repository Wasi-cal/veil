# A call to a dead Redis must fail fast, because a run makes many calls.
SOCKET_TIMEOUT_SECONDS = 0.25
# After a call fails, the cache leaves Redis alone for this long. Then it tries again.
COOLDOWN_SECONDS = 5.0
# Redis gives this time to live for a key that never expires.
NO_EXPIRY = -1
