import redis

from tests.adapters.jira.support import (
    API_TOKEN,
    DO_TRANSITION,
    FIELDS,
    ISSUE_TYPE,
    SEARCH,
    TRANSITIONS,
    make_tracker,
    reads,
    serve_status,
    transition,
)
from tests.fakes.http_server import StubHttpServer
from tests.fakes.jira_fixtures import search_page
from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.adapters.redis.jira_cache import RedisJiraMetadataCache
from veil.engine import Settings

SITE = "https://acme.atlassian.net"
MOVES = [
    {
        "id": "31",
        "to": {"name": "In Review", "statusCategory": {"key": "indeterminate"}},
    }
]


def jira_cache(url, ttl=300, site=SITE):
    return RedisJiraMetadataCache(
        GuardedRedis.from_url(url), ttl_seconds=ttl, site=site
    )


def test_the_field_ids_come_back_even_when_there_are_none(redis_url):
    cache = jira_cache(redis_url)
    assert cache.field_ids() is None

    cache.store_field_ids({})
    assert cache.field_ids() == {}
    cache.store_field_ids({"SonarQube Line": "customfield_10101"})
    assert cache.field_ids() == {"SonarQube Line": "customfield_10101"}


def test_the_transitions_of_a_project_and_a_status_come_back_and_can_be_forgotten(
    redis_url,
):
    cache = jira_cache(redis_url)

    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", MOVES)

    assert cache.transitions("SEC", ISSUE_TYPE, "To Do") == MOVES
    assert cache.transitions("SEC", ISSUE_TYPE, "In Progress") is None
    assert cache.transitions("OPS", ISSUE_TYPE, "To Do") is None
    cache.forget_transitions("SEC", ISSUE_TYPE, "To Do")
    assert cache.transitions("SEC", ISSUE_TYPE, "To Do") is None


def test_another_issue_type_does_not_share_the_transitions(redis_url):
    cache = jira_cache(redis_url)
    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", MOVES)

    assert cache.transitions("SEC", "10002", "To Do") is None


def test_the_lifetime_and_the_site_come_from_the_settings(redis_url):
    settings = Settings(cache_jira_metadata_ttl_seconds=45, jira_site_url=SITE)

    cache = RedisJiraMetadataCache.from_settings(
        GuardedRedis.from_url(redis_url), settings
    )
    cache.store_field_ids({})

    raw = redis.Redis.from_url(redis_url)
    [key] = raw.keys("veil:jira:*")
    assert 0 < raw.ttl(key) <= 45
    assert jira_cache(redis_url).field_ids() == {}


def test_every_entry_lives_for_the_jira_metadata_lifetime_of_the_settings(redis_url):
    cache = jira_cache(redis_url, ttl=120)

    cache.store_field_ids({})
    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", MOVES)

    raw = redis.Redis.from_url(redis_url)
    keys = raw.keys("veil:jira:*")
    assert len(keys) == 2
    assert all(0 < raw.ttl(key) <= 120 for key in keys)


def test_another_jira_site_does_not_share_the_entries(redis_url):
    jira_cache(redis_url, site="https://one.atlassian.net").store_field_ids({"a": "b"})

    assert jira_cache(redis_url, site="https://two.atlassian.net").field_ids() is None


def test_an_entry_that_is_not_json_or_has_the_wrong_shape_is_a_miss(redis_url):
    cache = jira_cache(redis_url)
    cache.store_field_ids({"a": "b"})
    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", MOVES)
    raw = redis.Redis.from_url(redis_url)
    for key in raw.keys("veil:jira:*"):
        raw.set(key, "not json" if b"fields" in key else '{"wrong": 1}')

    assert cache.field_ids() is None
    assert cache.transitions("SEC", ISSUE_TYPE, "To Do") is None


def test_with_redis_stopped_the_cache_gives_nothing_and_raises_nothing(stoppable_redis):
    cache = jira_cache(stoppable_redis.url)
    cache.store_field_ids({"a": "b"})
    stoppable_redis.stop()

    assert cache.field_ids() is None
    assert cache.transitions("SEC", ISSUE_TYPE, "To Do") is None
    cache.store_field_ids({"a": "b"})
    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", MOVES)
    cache.forget_transitions("SEC", ISSUE_TYPE, "To Do")


def test_two_runs_share_the_metadata_through_redis(redis_url):
    with StubHttpServer() as server:
        server.routes[FIELDS] = (200, [])
        server.routes[SEARCH] = (200, search_page([]))
        serve_status(server, "To Do", [transition("31", "In Review")])

        for _ in range(2):
            tracker = make_tracker(server, metadata_cache=jira_cache(redis_url))
            tracker.open_tickets()
            tracker.set_status("SEC-7", "In Review")

    assert reads(server, FIELDS) == 1
    assert reads(server, TRANSITIONS) == 1
    assert len([r for r in server.seen if (r.method, r.path) == DO_TRANSITION]) == 2


def test_with_redis_stopped_the_tracker_reads_jira_and_still_works(stoppable_redis):
    with StubHttpServer() as server:
        server.routes[FIELDS] = (200, [])
        server.routes[SEARCH] = (200, search_page([]))
        serve_status(server, "To Do", [transition("31", "In Review")])
        stoppable_redis.stop()

        for _ in range(2):
            tracker = make_tracker(
                server, metadata_cache=jira_cache(stoppable_redis.url)
            )
            tracker.open_tickets()
            tracker.set_status("SEC-7", "In Review")

    assert reads(server, FIELDS) == 2
    assert reads(server, TRANSITIONS) == 2


def test_redis_holds_no_jira_credential(redis_url):
    with StubHttpServer() as server:
        server.routes[FIELDS] = (200, [])
        server.routes[SEARCH] = (200, search_page([]))
        serve_status(server, "To Do", [transition("31", "In Review")])
        tracker = make_tracker(server, metadata_cache=jira_cache(redis_url))
        tracker.open_tickets()
        tracker.set_status("SEC-7", "In Review")

    raw = redis.Redis.from_url(redis_url)
    everything = b" ".join(key + b" " + (raw.get(key) or b"") for key in raw.keys("*"))
    assert API_TOKEN.encode() not in everything
    assert b"bot@example.invalid" not in everything
