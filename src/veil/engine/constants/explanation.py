import re

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
