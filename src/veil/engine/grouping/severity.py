from collections.abc import Mapping

from veil.engine.constants.severity import HIGH


def bucket_of(severity: str, severity_map: Mapping[str, str]) -> str:
    """Return the Severity Bucket of a severity word: high, medium or low.

    A word that is not in the map is high. Then the ticket gets its own PR and a person looks at it.
    """
    return severity_map.get(severity.strip().upper(), HIGH)
