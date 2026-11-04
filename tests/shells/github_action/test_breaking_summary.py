from tests.shells.github_action.support import SpyRun
from veil.engine import RunReport


def test_the_summary_lists_the_breaking_fixes_with_their_reason(world):
    report = RunReport(
        outcomes={"SEC-1": "fixed", "SEC-2": "fixed"},
        breaking={"SEC-1": "The function a|b no\nlonger takes a string."},
    )

    world.run_action(run=SpyRun(world.out, report=report))

    text = world.summary.read_text()
    section = text.split("### Breaking changes")[1]
    assert "| SEC-1 | The function a\\|b no longer takes a string. |" in section
    assert "SEC-2" not in section


def test_the_summary_has_no_breaking_section_when_no_fix_is_breaking(world):
    report = RunReport(outcomes={"SEC-1": "fixed"})

    world.run_action(run=SpyRun(world.out, report=report))

    assert "Breaking changes" not in world.summary.read_text()
