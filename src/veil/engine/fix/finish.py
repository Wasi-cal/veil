import re
from difflib import SequenceMatcher

from pydantic import ValidationError

from veil.engine.constants.explanation import (
    ABBREVIATIONS,
    COPY_SHARE,
    MAX_SENTENCE_WORDS,
    MIN_COPY_WORDS,
    SENTENCE_END,
)
from veil.engine.models.config.settings import Settings
from veil.engine.models.llm.tool_call import ToolCall
from veil.engine.models.tool_args.finish_args import FinishArgs


def count_sentences(text: str) -> int:
    """Count the sentences of a text. A text without an end mark counts as one sentence."""
    text = text.strip()
    count = sum(
        1 for mark in SENTENCE_END.finditer(text) if not _abbreviation(text, mark)
    )
    return max(count, 1)


def longest_sentence_words(text: str) -> int:
    """The number of words in the longest sentence of a text."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return max(len(sentence.split()) for sentence in sentences)


def _abbreviation(text: str, mark: re.Match[str]) -> bool:
    """Check if the mark ends an abbreviation, such as "etc.". An abbreviation does not end a sentence."""
    before = text[: mark.end()].lower()
    return any(
        before.endswith(word)
        and (len(before) == len(word) or not before[-len(word) - 1].isalnum())
        for word in ABBREVIATIONS
    )


def read_finish(
    call: ToolCall, settings: Settings, finding_text: str = ""
) -> FinishArgs | str:
    """Return the arguments of a finish call. If they break the format, return an error text for the model.

    Each of the three parts must be short, with short sentences. No part may copy the text of the ticket.
    """
    try:
        args = FinishArgs.model_validate(call.arguments)
    except ValidationError as error:
        problem = error.errors()[0]["msg"].removeprefix("Value error, ")
        return f"Error: The arguments of finish are not valid. {problem}"
    limit = settings.explanation_max_sentences
    for name in ("problem", "change", "solves"):
        text = getattr(args, name)
        if count_sentences(text) > limit:
            return f"Error: The part {name} has more than {limit} sentences. Use at most {limit} sentences."
        if longest_sentence_words(text) > MAX_SENTENCE_WORDS:
            return f"Error: A sentence of the part {name} has more than {MAX_SENTENCE_WORDS} words. Use short sentences."
        if copies_text(text, finding_text):
            return f"Error: The part {name} copies the text of the ticket. Describe this code in your own words."
    return args


def copies_text(text: str, source: str) -> bool:
    """Check if `text` copies `source`. It copies if it is inside the source word for word.

    A long text also copies if a big share of its words is one run of the words of the source.
    """
    words = re.findall(r"[a-z0-9_]+", text.lower())
    source_words = re.findall(r"[a-z0-9_]+", source.lower())
    if len(words) < MIN_COPY_WORDS or not source_words:
        return False
    joined, source_joined = " ".join(words), " ".join(source_words)
    if joined in source_joined:
        return True
    match = SequenceMatcher(
        None, words, source_words, autojunk=False
    ).find_longest_match(0, len(words), 0, len(source_words))
    return match.size / len(words) >= COPY_SHARE
