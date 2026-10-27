from tests.fakes import (
    FakeModelClient,
    FakeRepoProvider,
    FakeTracker,
    edit_file,
    finish,
    make_ticket,
)
from veil.engine import Context, Settings

VULNERABLE = "import os\n\nvalue = eval(input())\n"
FIXED = "import os\n\nvalue = int(input())\n"
GOOD_EDIT = edit_file("app.py", "eval(input())", "int(input())")
EDIT_THEN_FINISH = [
    [edit_file("app.py", "eval(input())", "int(input())")],
    [finish("Replaced eval with int.")],
]


def toggle_edits(count):
    """`count` valid edits that change the same text back and forth. None of them finishes the attempt."""
    pairs = [("eval(input())", "int(input())"), ("int(input())", "eval(input())")]
    return [[edit_file("app.py", *pairs[n % 2])] for n in range(count)]


def make_context(
    tmp_path,
    model_script,
    tokens_per_call=0,
    files=None,
    settings=None,
    extra_tickets=(),
    **ticket_fields,
):
    fields = {
        "key": "GR-100",
        "repo": "acme/app",
        "file": "app.py",
        "line": 3,
        **ticket_fields,
    }
    ticket = make_ticket(**fields)
    others = [make_ticket(**{**fields, **extra}) for extra in extra_tickets]
    tracker = FakeTracker([ticket, *others])
    repos = FakeRepoProvider(tmp_path, {"acme/app": files or {"app.py": VULNERABLE}})
    model = FakeModelClient(model_script, tokens_per_call=tokens_per_call)
    context = Context(
        settings=settings or Settings(),
        tracker=tracker,
        repo_provider=repos,
        model_client=model,
    )
    return context, tracker, repos, model


def assert_failed_fix(tracker, repos, report, key="GR-100"):
    """Check a Failed Fix. There is no PR. The ticket stays open. It has a reason comment and the marker label."""
    assert repos.pull_requests == []
    assert report.outcomes[key] == "failed"
    assert tracker.status_of(key) == "To Do"
    assert tracker.labels_on(key) == ["veil-failed-fix"]
    [comment] = tracker.comments_on(key)
    return comment
