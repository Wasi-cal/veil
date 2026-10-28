from tests.adapters.jira.support import make_tracker
from tests.fakes.http_server import StubHttpServer

COMMENTS = "/rest/api/3/issue/SEC-7/comment"
LIST = ("GET", COMMENTS)
POST = ("POST", COMMENTS)
TEXT = "Veil opened a draft PR.\nhttps://github.example.invalid/acme/app/pull/9"


def no_comments() -> tuple:
    return (200, {"comments": [], "startAt": 0, "maxResults": 100, "total": 0})


def sent(server: StubHttpServer):
    return [r for r in server.seen if (r.method, r.path) == POST]


def comment_with(properties: list[dict]) -> dict:
    return {"id": "9001", "properties": properties}


def test_a_comment_is_posted_with_its_text_and_a_hidden_marker():
    with StubHttpServer() as server:
        server.routes[LIST] = no_comments()
        server.routes[POST] = (201, {"id": "9001"})

        make_tracker(server).add_comment("SEC-7", TEXT)

    [post] = sent(server)
    paragraphs = post.body["body"]["content"]
    assert [p["content"][0]["text"] for p in paragraphs] == TEXT.split("\n")
    [prop] = post.body["properties"]
    assert prop["key"] == "veil"
    assert prop["value"]["marker"]
    assert TEXT not in str(prop)


def test_the_same_comment_is_not_posted_twice():
    with StubHttpServer() as server:
        server.routes[LIST] = no_comments()
        server.routes[POST] = (201, {"id": "9001"})
        make_tracker(server).add_comment("SEC-7", TEXT)
        [first] = sent(server)
        server.routes[LIST] = (
            200,
            {
                "comments": [comment_with(first.body["properties"])],
                "startAt": 0,
                "maxResults": 100,
                "total": 1,
            },
        )

        make_tracker(server).add_comment("SEC-7", TEXT)

    assert len(sent(server)) == 1


def test_a_different_text_is_posted_even_when_another_marker_exists():
    with StubHttpServer() as server:
        server.routes[LIST] = no_comments()
        server.routes[POST] = (201, {"id": "9001"})
        make_tracker(server).add_comment("SEC-7", TEXT)
        [first] = sent(server)
        server.routes[LIST] = (
            200,
            {
                "comments": [comment_with(first.body["properties"])],
                "startAt": 0,
                "maxResults": 100,
                "total": 1,
            },
        )

        make_tracker(server).add_comment("SEC-7", "A different text.")

    assert len(sent(server)) == 2


def test_a_person_comment_with_the_same_words_does_not_count_as_a_marker():
    with StubHttpServer() as server:
        server.routes[LIST] = (
            200,
            {
                "comments": [comment_with([])],
                "startAt": 0,
                "maxResults": 100,
                "total": 1,
            },
        )
        server.routes[POST] = (201, {"id": "9002"})

        make_tracker(server).add_comment("SEC-7", TEXT)

    assert len(sent(server)) == 1


def test_a_marker_on_a_later_page_of_comments_is_found():
    with StubHttpServer() as server:
        server.routes[LIST] = no_comments()
        server.routes[POST] = (201, {"id": "9001"})
        make_tracker(server).add_comment("SEC-7", TEXT)
        [first] = sent(server)
        server.routes[LIST] = [
            (
                200,
                {
                    "comments": [comment_with([])],
                    "startAt": 0,
                    "maxResults": 1,
                    "total": 2,
                },
            ),
            (
                200,
                {
                    "comments": [comment_with(first.body["properties"])],
                    "startAt": 1,
                    "maxResults": 1,
                    "total": 2,
                },
            ),
        ]

        make_tracker(server).add_comment("SEC-7", TEXT)

    assert len(sent(server)) == 1
    reads = [r for r in server.seen if (r.method, r.path) == LIST]
    assert reads[-1].query["startAt"] == ["1"]
    assert reads[-1].query["expand"] == ["properties"]
