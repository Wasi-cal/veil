import re

# A mark ends a sentence if white space or the end of the text follows it. "a.py" does not end one.
SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")
# A word with a full stop that is not the end of a sentence.
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "cf.")
