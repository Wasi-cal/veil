import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import (
    CHEAP,
    CREDENTIAL,
    EDIT_THEN_FINISH,
    FIXED,
    STRONG,
    VULNERABLE,
    assert_failed_fix,
    assert_nowhere,
    both_attempts,
    make_context,
)
from veil.engine import run


def edit_that_adds(text):
    """An edit that fixes the bug and adds `text` as a comment on the same line."""
    return [
        [edit_file("app.py", "eval(input())", f"int(input())  # {text}")],
        [finish("Replaced eval with int.")],
    ]


def test_a_credential_of_this_run_in_an_added_line_fails_the_attempt_and_the_strong_attempt_gets_one_try(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path,
        {CHEAP: edit_that_adds(CREDENTIAL), STRONG: EDIT_THEN_FINISH},
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED
    assert_nowhere(CREDENTIAL, tracker, repos, report, model=model)


def test_if_both_attempts_add_the_credential_the_ticket_is_a_failed_fix_and_the_comment_names_no_value(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path,
        both_attempts(edit_that_adds(CREDENTIAL)),
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert "credential" in comment.lower()
    assert_nowhere(CREDENTIAL, tracker, repos, report, model=model)


# Fake keys. Each one is built from pieces, so no key-like text sits in this file.
KEY_LIKE = {
    "rsa-private-key-header": "-----BEGIN " + "RSA PRIVATE KEY-----",
    "openssh-private-key-header": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
    "aws-access-key-id": "AK" + "IA" + "IOSFODNN7EXAMPLE",
    "github-token": "gh" + "p_" + "A1" * 18,
    "google-api-key": "AI" + "za" + "SyA-" + "x" * 31,
    "slack-token": "xo" + "xb-" + "123456789012-abcdefghijkl",
    "sk-key": "s" + "k-" + "proj" + "a1" * 12,
    "atlassian-token": "AT" + "ATT3" + "xFfGF0" + "b" * 24,
}


@pytest.mark.parametrize("secret", list(KEY_LIKE.values()), ids=list(KEY_LIKE))
def test_a_secret_pattern_in_an_added_line_fails_the_attempt(tmp_path, secret):
    context, tracker, repos, model = make_context(
        tmp_path,
        {CHEAP: edit_that_adds(secret), STRONG: EDIT_THEN_FINISH},
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED
    assert_nowhere(secret, tracker, repos, report, model=model)


def test_secret_like_text_that_is_already_in_the_file_does_not_block_the_fix(tmp_path):
    old_key = KEY_LIKE["aws-access-key-id"]
    context, _, repos, _ = make_context(
        tmp_path,
        EDIT_THEN_FINISH,
        files={"app.py": f"import os\n\nvalue = eval(input())\n# old: {old_key}\n"},
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert repos.commit_subjects_on(pr) == ["Fix the finding."]


@pytest.mark.parametrize(
    "honest",
    [
        "see the sk-learn docs",
        "the AKIA prefix of an access key id",
        "a token such as ghp_ is not allowed here",
        "BEGIN PRIVATE KEY is a header name",
    ],
)
def test_text_that_only_looks_a_little_like_a_key_is_not_a_secret(tmp_path, honest):
    context, _, _, _ = make_context(tmp_path, edit_that_adds(honest))

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}


@pytest.mark.parametrize(
    "secret",
    [CREDENTIAL, KEY_LIKE["github-token"]],
    ids=["credential-of-this-run", "github-token"],
)
@pytest.mark.parametrize("where", ["explanation", "commit_message"])
def test_a_secret_in_the_explanation_or_the_commit_message_fails_the_attempt(
    tmp_path, secret, where
):
    bad_finish = (
        finish(f"The value {secret} is gone.")
        if where == "explanation"
        else finish("Fixed.", commit_message=f"Remove {secret}")
    )
    context, tracker, repos, model = make_context(
        tmp_path,
        {
            CHEAP: [
                [edit_file("app.py", "eval(input())", "int(input())")],
                [bad_finish],
            ],
            STRONG: EDIT_THEN_FINISH,
        },
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert_nowhere(secret, tracker, repos, report, model=model)


def test_the_redaction_net_hides_a_credential_in_a_ticket_field_in_the_failed_fix_comment(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path,
        [[finish("Nothing.")]],
        file=f"{CREDENTIAL}.py",
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert "[redacted].py" in comment
    assert_nowhere(CREDENTIAL, tracker, repos, report, model=model)


def test_the_redaction_net_hides_a_credential_in_the_pr_body_and_the_ticket_comment(
    tmp_path,
):
    two_bugs = "first = eval(input())\nsecond = eval(input())\n"
    path = f"{CREDENTIAL}.py"
    context, tracker, repos, model = make_context(
        tmp_path,
        [
            [edit_file(path, "first = eval(input())", "first = int(input())")],
            [finish("Fixed first.", commit_message="Fix first")],
            [edit_file(path, "second = eval(input())", "second = int(input())")],
            [finish("Fixed second.", commit_message="Fix second")],
        ],
        files={path: two_bugs},
        file=path,
        severity="High",
        line=1,
        extra_tickets=[{"key": "GR-101", "line": 2}],
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed", "GR-101": "fixed"}
    [pr] = repos.pull_requests
    assert "[redacted].py" in pr.body
    assert "Fixed first." in pr.body
    assert "Fixed second." in pr.body
    for key in ("GR-100", "GR-101"):
        assert any("Fixed" in comment for comment in tracker.comments_on(key))
    assert_nowhere(
        CREDENTIAL,
        tracker,
        repos,
        report,
        keys=("GR-100", "GR-101"),
        model=model,
    )


def test_a_key_that_is_already_on_an_edited_line_does_not_block_the_fix(tmp_path):
    """The model edits only the comment of a line. The line already holds a key, so the Fix adds no secret."""
    old_key = KEY_LIKE["aws-access-key-id"]
    context, tracker, _, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", "# old", "# changed")],
            [edit_file("app.py", "eval(input())", "int(input())")],
            [finish("Fixed.")],
        ],
        files={
            "app.py": f'import os\n\nvalue = eval(input())\nkey = "{old_key}"  # old\n'
        },
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert tracker.labels_on("GR-100") == []


def test_a_key_pattern_in_a_failure_reason_does_not_reach_the_ticket_comment(tmp_path):
    key = KEY_LIKE["aws-access-key-id"]
    context, tracker, repos, _ = make_context(
        tmp_path, [[finish("Nothing.")]], file=f"{key}.py"
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert key not in comment
    assert "[redacted].py" in comment


def test_a_parser_error_that_would_repeat_a_key_name_does_not_reach_the_comment(
    tmp_path,
):
    key = KEY_LIKE["aws-access-key-id"]
    bad_toml = [
        [edit_file("conf.toml", "[a]", f"[a.{key}]\n[a.{key}]")],
        [finish("Changed the table.")],
    ]
    context, tracker, repos, _ = make_context(
        tmp_path,
        both_attempts(bad_toml),
        files={"conf.toml": "[a]\nx = 1\n"},
        file="conf.toml",
        line=1,
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert key not in comment
    assert "AWS access key id" in comment


def test_the_run_report_never_holds_a_credential_even_in_a_ticket_key(tmp_path):
    context, _, _, _ = make_context(
        tmp_path,
        both_attempts([[finish("Nothing.")]]),
        key=f"GR-{CREDENTIAL}",
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    assert CREDENTIAL not in report.model_dump_json()
    assert report.outcomes == {"GR-[redacted]": "failed"}


def test_the_model_never_gets_a_credential_from_the_ticket_or_the_file(tmp_path):
    github_key = KEY_LIKE["github-token"]
    source = f'{VULNERABLE}token = "{CREDENTIAL}"\nkey = "{github_key}"\n'
    context, _, _, model = make_context(
        tmp_path,
        EDIT_THEN_FINISH,
        files={"app.py": source},
        finding=f"Avoid eval. A leak of {CREDENTIAL} was seen.",
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    received = model.sent_by_the_engine()
    assert CREDENTIAL not in received
    assert github_key not in received
    assert "value = eval(input())" in received
    assert "[redacted]" in model.first_prompt()
