"""Read the text of an Atlassian Document Format (ADF) description. Jira sends rich text in this JSON format."""

from veil.adapters.jira.constants.details import DETAILS_HEADING


def text_of(node: dict) -> str:
    """The plain text of a node and its children."""
    if node.get("type") == "text":
        return node.get("text", "")
    return "".join(text_of(child) for child in node.get("content", []))


def _walk(node: dict):
    yield node
    for child in node.get("content", []):
        yield from _walk(child)


def finding_text(description: dict) -> str:
    """The full text of the finding. It is in the expand block when Gozurion cut the first paragraph short."""
    nodes = list(_walk(description))
    for node in nodes:
        if node.get("type") == "expand":
            return text_of(node).strip()
    for node in nodes:
        if node.get("type") == "paragraph":
            return text_of(node).strip()
    return ""


def details_of(description: dict) -> dict[str, str]:
    """The `Name: value` lines of the list that follows the Details heading.

    Only that list counts. A bullet in the text of the finding must never win over it.
    """
    found: dict[str, str] = {}
    after_heading = False
    for node in description.get("content", []):
        if node.get("type") == "heading":
            after_heading = text_of(node).strip() == DETAILS_HEADING
        elif after_heading and node.get("type") == "bulletList":
            for item in node.get("content", []):
                name, separator, value = text_of(item).partition(":")
                if separator:
                    found.setdefault(name.strip(), value.strip())
            break
    return found


def comment_body(text: str) -> dict:
    """An ADF document for a comment. Each non-empty line is one paragraph."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": line}]}
            for line in text.splitlines()
            if line.strip()
        ],
    }
