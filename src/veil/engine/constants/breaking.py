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
