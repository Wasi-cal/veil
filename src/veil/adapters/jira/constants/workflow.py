# The status category of a closed ticket. The adapter never moves a ticket into it.
DONE_CATEGORY = "done"
# The key of the comment property that holds the hidden marker. The property is not visible in Jira.
COMMENT_PROPERTY_KEY = "veil"
# A failed move with one of these statuses can mean that the cached transition is old. Jira says the move is not valid.
STALE_TRANSITION_STATUSES = frozenset({400, 404, 409})
