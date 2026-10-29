from typing import Literal

Bucket = Literal["high", "medium", "low"]

HIGH: Bucket = "high"
MEDIUM: Bucket = "medium"
LOW: Bucket = "low"

# How serious a bucket is. A higher number is more serious.
BUCKET_RANK: dict[Bucket, int] = {LOW: 0, MEDIUM: 1, HIGH: 2}

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
