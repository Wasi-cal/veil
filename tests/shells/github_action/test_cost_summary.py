from tests.shells.github_action.support import SpyRun
from veil.engine import RunReport
from veil.engine.models.report.ticket_usage import ModelTokens, TicketUsage

LUNA, TERRA = "gpt-6-luna", "gpt-6.1-terra"


def usage(escalated=False, **by_model):
    return TicketUsage(by_model=by_model, escalated=escalated)


def report():
    return RunReport(
        outcomes={"VT-1": "fixed", "VT-2": "fixed"},
        usage={
            "VT-1": usage(
                escalated=True,
                **{
                    LUNA: ModelTokens(
                        input=10000, cached=8000, output=1000, total=11000
                    ),
                    TERRA: ModelTokens(input=5000, cached=0, output=500, total=5500),
                },
            ),
            "VT-2": usage(
                **{LUNA: ModelTokens(input=4000, cached=1000, output=400, total=4400)}
            ),
        },
    )


def section(text: str, heading: str) -> list[str]:
    return text.split(heading)[1].split("###")[0].strip().splitlines()


def test_the_summary_ends_with_the_cost_of_each_model_and_the_total(world):
    world.run_action(run=SpyRun(world.out, report=report()))

    text = world.summary.read_text()
    rows = section(text, "### Cost")
    # luna: 5000 uncached x 0.10 + 9000 cached x 0.01 = $0.00059 in, 1400 x 0.50 = $0.0007 out
    assert "| gpt-6-luna | 5000 | 9000 | 1400 | $0.0006 | $0.0007 | $0.0013 |" in rows
    # terra: 5000 x 1.00 = $0.005 in, 500 x 5.00 = $0.0025 out
    assert "| gpt-6.1-terra | 5000 | 0 | 500 | $0.0050 | $0.0025 | $0.0075 |" in rows
    assert "| **Total** | 10000 | 9000 | 1900 | $0.0056 | $0.0032 | $0.0088 |" in rows
    assert text.rindex("### Cost") > text.rindex("### Escalated tickets")


def test_the_escalated_table_shows_the_cost_of_each_model_of_the_ticket(world):
    world.run_action(run=SpyRun(world.out, report=report()))

    rows = section(world.summary.read_text(), "### Escalated tickets")
    assert "| VT-1 | gpt-6-luna | 10000 | 1000 | 11000 | $0.0003 | $0.0005 |" in rows
    assert "| VT-1 | gpt-6.1-terra | 5000 | 500 | 5500 | $0.0050 | $0.0025 |" in rows


def test_a_model_without_a_price_shows_na_and_stays_out_of_the_total(world):
    unknown = RunReport(
        outcomes={"VT-1": "fixed"},
        usage={"VT-1": usage(mystery=ModelTokens(input=100, output=10, total=110))},
    )

    world.run_action(run=SpyRun(world.out, report=unknown))

    rows = section(world.summary.read_text(), "### Cost")
    assert "| mystery | 100 | 0 | 10 | n/a | n/a | n/a |" in rows
    assert any("No price for `mystery`" in row for row in rows)


def test_a_run_with_no_model_call_has_no_cost_section(world):
    world.run_action(run=SpyRun(world.out, report=RunReport()))

    assert "### Cost" not in world.summary.read_text()
