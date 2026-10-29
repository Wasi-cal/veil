from tests.fakes.jira_fixtures import gozurion_details, issue_json, search_page
from tests.shells.github_action.support import SEARCH, SpyRun


def test_the_tracker_of_the_action_returns_only_tickets_of_its_own_repo(world):
    world.jira.routes[SEARCH] = (
        200,
        search_page(
            [
                issue_json("SEC-1"),
                issue_json("SEC-2", details=gozurion_details(repo="acme/other")),
                issue_json("SEC-3", details=gozurion_details(repo="evil/app")),
            ]
        ),
    )
    seen = []

    class Caller(SpyRun):
        def __call__(self, context):
            seen.extend(t.key for t in context.tracker.open_tickets())
            return super().__call__(context)

    code, _, _ = world.run_action(run=Caller(world.out))

    assert code == 0
    assert seen == ["SEC-1"]
