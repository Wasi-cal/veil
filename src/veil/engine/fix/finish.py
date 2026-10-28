import re

from pydantic import ValidationError

from veil.engine.models.config.settings import Settings
from veil.engine.models.llm.tool_call import ToolCall
from veil.engine.models.tool_args.finish_args import FinishArgs

# A mark ends a sentence if a capital letter follows, or the text ends. "e.g. a.py" does not end one.
_SENTENCE_END = re.compile(r"[.!?]+(?=\s+[A-Z]|\s*$)")


def count_sentences(text: str) -> int:
    """Count the sentences of a text. A text without an end mark counts as one sentence."""
    return max(len(_SENTENCE_END.findall(text.strip())), 1)


def read_finish(call: ToolCall, settings: Settings) -> FinishArgs | str:
    """Return the arguments of a finish call, or the error text for the model if they break the format."""
    try:
        args = FinishArgs.model_validate(call.arguments)
    except ValidationError as error:
        problem = error.errors()[0]["msg"].removeprefix("Value error, ")
        return f"Error: The arguments of finish are not valid. {problem}"
    limit = settings.explanation_max_sentences
    if count_sentences(args.explanation) > limit:
        return f"Error: The explanation has more than {limit} sentences. Use at most {limit} sentences."
    return args
