import re

from pydantic import ValidationError

from veil.engine.models.config.settings import Settings
from veil.engine.models.llm.tool_call import ToolCall
from veil.engine.models.tool_args.finish_args import FinishArgs

# A mark ends a sentence if white space or the end of the text follows it. "a.py" does not end one.
_SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")
# A word with a full stop that is not the end of a sentence.
_ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "cf.")


def count_sentences(text: str) -> int:
    """Count the sentences of a text. A text without an end mark counts as one sentence."""
    text = text.strip()
    count = sum(
        1 for mark in _SENTENCE_END.finditer(text) if not _abbreviation(text, mark)
    )
    return max(count, 1)


def _abbreviation(text: str, mark: re.Match[str]) -> bool:
    """Check if the mark ends an abbreviation, such as "etc.". An abbreviation does not end a sentence."""
    before = text[: mark.end()].lower()
    return any(
        before.endswith(word)
        and (len(before) == len(word) or not before[-len(word) - 1].isalnum())
        for word in _ABBREVIATIONS
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
    return args
