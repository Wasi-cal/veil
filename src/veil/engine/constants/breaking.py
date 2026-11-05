import re

# What the Engine says about a Breaking change that its own checks found. Each reason is one sentence in ASD-STE100.
# A Fix shows at most this many reasons. The reason of the model comes first.
MAX_BREAKING_REASONS = 5

# The kinds of a parameter that a caller can pass by position.
POSITIONAL_KINDS = ("posonly", "pos")

REMOVED_REASON = "The public {kind} `{name}` in {path} is removed or renamed."
PARAMETERS_REASON = (
    "The parameters of the public {kind} `{name}` in {path} changed. "
    "A caller that works now can fail."
)

# The manifests that the Engine compares, by file name.
MANIFEST_NAMES = ("package.json", "pyproject.toml", "requirements.txt")

# The keys of `package.json` that list dependencies.
NPM_DEPENDENCY_KEYS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)

# A requirement line longer than this is not read. A very long line can stall the pattern below.
MAX_REQUIREMENT_LINE = 1000

# A name at the start of a requirement line, and the first version in a version text.
REQUIREMENT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
VERSION_NUMBER = re.compile(r"\d+(?:\.\d+)*")

MAJOR_REASON = (
    "The dependency `{name}` in {path} goes from {old} to {new}. "
    "A version change of this size can break the code that uses it."
)
RUNTIME_REASON = (
    "The `{name}` version that {path} requires goes from {old} to {new}. "
    "A user on an older version can fail."
)
DEPENDENCY_REMOVED_REASON = (
    "The dependency `{name}` is removed from {path}. The code that uses it can fail."
)
