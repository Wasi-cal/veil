import re

from pydantic import ValidationError

from veil.engine.constants.explanation import (
    ABBREVIATIONS,
    MAX_SENTENCE_WORDS,
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


def read_finish(call: ToolCall, settings: Settings) -> FinishArgs | str:
    """Return the arguments of a finish call. If they break the format, return an error text for the model."""
    try:
        args = FinishArgs.model_validate(call.arguments)
    except ValidationError as error:
        problem = error.errors()[0]["msg"].removeprefix("Value error, ")
        return f"Error: The arguments of finish are not valid. {problem}"
    limit = settings.explanation_max_sentences
    if count_sentences(args.explanation) > limit:
        return f"Error: The explanation has more than {limit} sentences. Use at most {limit} sentences."
    if longest_sentence_words(args.explanation) > MAX_SENTENCE_WORDS:
        return f"Error: A sentence of the explanation has more than {MAX_SENTENCE_WORDS} words. Use short sentences."
    return args
