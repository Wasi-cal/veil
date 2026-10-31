from tests.fakes import edit_file, finish
from tests.support.scenario import make_context
from veil.engine import run

LONG_SENTENCE = (
    "This change replaces the call to the function that evaluates text with a safe "
    "parser so that an attacker can no longer run any code through the input of the user."
)


def one_fix(explanation, commit_message="Replace eval with int."):
    return [
        [edit_file("app.py", "eval(input())", "int(input())")],
        [finish(explanation, commit_message=commit_message)],
    ]


def test_the_title_of_a_shared_pr_with_one_ticket_says_ticket_in_the_singular(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path, one_fix("Replaced eval with int."), severity="Medium"
    )

    run(context)

    [pr] = repos.pull_requests
    assert pr.title == "Fix 1 ticket"


def test_an_explanation_with_a_long_sentence_is_refused_and_the_model_gets_a_second_try(
    tmp_path,
):
    short = "Replaced eval with int. The input is now a number."
    context, _tracker, repos, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", "eval(input())", "int(input())")],
            [finish(LONG_SENTENCE)],
            [finish(short)],
        ],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert short in pr.body
    assert LONG_SENTENCE not in pr.body


def test_an_explanation_of_short_sentences_is_used_as_it_is(tmp_path):
    text = "Replaced eval with int. The input is now a number."
    context, _, repos, _ = make_context(tmp_path, one_fix(text))

    run(context)

    [pr] = repos.pull_requests
    assert text in pr.body
