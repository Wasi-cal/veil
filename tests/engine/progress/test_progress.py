import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import EDIT_THEN_FINISH, make_context
from veil.engine import run


class Recorder:
    def __init__(self):
        self.values: list[int] = []

    def __call__(self, tokens_used: int) -> None:
        self.values.append(tokens_used)


def test_progress_reports_the_tokens_used_after_each_model_call(tmp_path):
    recorder = Recorder()
    context, _, _, _ = make_context(
        tmp_path, EDIT_THEN_FINISH, tokens_per_call=10, progress=recorder
    )

    report = run(context)

    assert report.tokens_used == 20
    assert 10 in recorder.values
    assert recorder.values[-1] == 20
    assert recorder.values == sorted(recorder.values)


def test_progress_reports_after_each_ticket_even_when_no_tokens_are_used(tmp_path):
    recorder = Recorder()
    context, _, _, _ = make_context(
        tmp_path,
        [
            [edit_file("app.py", "eval(input())", "int(input())")],
            [finish("Fixed app.")],
            [edit_file("other.py", "eval(input())", "int(input())")],
            [finish("Fixed other.")],
        ],
        progress=recorder,
        extra_tickets=[{"key": "GR-101", "file": "other.py"}],
        files={"app.py": "value = eval(input())\n", "other.py": "x = eval(input())\n"},
    )

    report = run(context)

    assert len(report.outcomes) == 2
    # Four model calls and two tickets give at least six reports.
    assert len(recorder.values) >= 6


def test_a_run_with_no_progress_callback_works(tmp_path):
    context, _, _, _ = make_context(tmp_path, EDIT_THEN_FINISH)

    assert run(context).outcomes == {"GR-100": "fixed"}


def test_an_error_of_the_callback_stops_the_run_and_reaches_the_caller(tmp_path):
    def cancel(_tokens: int) -> None:
        raise RuntimeError("cancelled")

    context, _, _, _ = make_context(tmp_path, EDIT_THEN_FINISH, progress=cancel)

    with pytest.raises(RuntimeError, match="cancelled"):
        run(context)


def test_progress_reports_after_a_ticket_that_failed_before_any_model_call(tmp_path):
    recorder = Recorder()
    context, _, _, _ = make_context(
        tmp_path, EDIT_THEN_FINISH, progress=recorder, file="missing.py"
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "failed"}
    assert recorder.values == [0]
