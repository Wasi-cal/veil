# The words that end a problem line. Each says what is wrong and never repeats the value.
MUST_BE_WHOLE_NUMBER = "must be a whole number"
MUST_BE_TEXT = "must be text"
MUST_BE_LIST = "must be a list"
MUST_BE_TRUE_OR_FALSE = "must be true or false"
VALUE_NOT_ALLOWED = "has a value that is not allowed"
VALUE_NOT_VALID = "has a value that is not valid"
# The last words of the problem line for a value that looks like a secret.
NO_SECRETS = "Settings hold no secrets."
# The names of the layers in a problem line.
LAYER_ORG = "org settings"
LAYER_REPO = "repo settings"
LAYER_OVERRIDES = "overrides"


# How a message names a key that it must not repeat.
KEY_LOOKS_LIKE_SECRET = "a key that looks like a secret"
KEY_NOT_TEXT = "a key that is not text"
KEY_TOO_LONG = "a key that is too long"
MAX_KEY_CHARS_IN_MESSAGE = 60
# More words for the problem lines. The first three come from the bounds on a value.
TOO_LONG = "is too long"
TOO_MANY_ENTRIES = "has too many entries"
ENTRY_TOO_LONG = "has an entry that is too long"
WORD_TWICE = "names a word twice"

# What is wrong, by the type of the error that the check gives.
WORDS_BY_ERROR_TYPE = {
    "int_parsing": MUST_BE_WHOLE_NUMBER,
    "int_type": MUST_BE_WHOLE_NUMBER,
    "int_from_float": MUST_BE_WHOLE_NUMBER,
    "string_type": MUST_BE_TEXT,
    "bool_parsing": MUST_BE_TRUE_OR_FALSE,
    "bool_type": MUST_BE_TRUE_OR_FALSE,
    "tuple_type": MUST_BE_LIST,
    "list_type": MUST_BE_LIST,
    "literal_error": VALUE_NOT_ALLOWED,
    "string_pattern_mismatch": VALUE_NOT_ALLOWED,
    "string_too_short": VALUE_NOT_ALLOWED,
    "value_error": VALUE_NOT_ALLOWED,
    "string_too_long": TOO_LONG,
    "too_long": TOO_MANY_ENTRIES,
    "entry_too_long": ENTRY_TOO_LONG,
    "word_twice": WORD_TWICE,
}
