# The model-call limit is for one minute. A count starts again each minute.
RATE_WINDOW_SECONDS = 60
# A counter lives for two windows, so a late worker still finds it. Then Redis removes it.
RATE_KEY_LIFETIME_SECONDS = 120
