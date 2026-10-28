from typing import Literal

Bucket = Literal["high", "medium", "low"]

HIGH: Bucket = "high"
MEDIUM: Bucket = "medium"
LOW: Bucket = "low"

# Gozu uses the Sonar words. The plain words map to themselves.
DEFAULT_SEVERITY_MAP: dict[str, Bucket] = {
    "BLOCKER": HIGH,
    "CRITICAL": HIGH,
    "MAJOR": MEDIUM,
    "MINOR": LOW,
    "INFO": LOW,
    "HIGH": HIGH,
    "MEDIUM": MEDIUM,
    "LOW": LOW,
}
