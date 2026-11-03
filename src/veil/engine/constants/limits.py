# Limits, bounds, defaults of the triggers and the rules of the explanation.
import re

# --- limits ---
STEP_CAP = 25
DIFF_LIMIT = 200
READ_FILE_MAX_LINES = 300
SEARCH_MAX_MATCHES = 50
TOOL_RESULT_MAX_BYTES = 8 * 1024
TOKEN_CEILING = 100_000
EXPLANATION_MAX_SENTENCES = 3
MIN_SECRET_LENGTH = 8
MIN_TOOL_RESULT_MAX_BYTES = 256
# One attempt with the cheap model, then one with the strong model.
MAX_ATTEMPTS = 2
# The attempt number from which the strong model runs.
STRONG_MODEL_ATTEMPT = 2

# --- settings_bounds ---
# The longest text and the longest list that a setting may hold. A longer value is a mistake or an attack.
MAX_NAME_CHARS = 100
MAX_URL_CHARS = 300
MAX_ENTRY_CHARS = 200
MAX_LIST_ENTRIES = 200

# --- triggers ---
# The fewest automatic runs are the safe default. A run on demand and a run for an event are on.
SCHEDULE_ENABLED = False
ON_DEMAND_ENABLED = True
EVENT_ENABLED = True

# --- explanation ---
# A mark ends a sentence if white space or the end of the text follows it. "a.py" does not end one.
SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")
# A word with a full stop that is not the end of a sentence.
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "cf.")
# ASD-STE100 allows at most 25 words in a sentence. A longer sentence in the explanation goes back to the model.
MAX_SENTENCE_WORDS = 25
# A part of the explanation copies the ticket if this share of its words is one run of the words of the ticket.
COPY_SHARE = 0.6
# A part with fewer words cannot copy. A short phrase may match by chance.
MIN_COPY_WORDS = 4
