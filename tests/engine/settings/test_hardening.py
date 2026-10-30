import pytest
from pydantic import ValidationError

from veil.engine import Settings, SettingsError, resolve_settings

GITHUB_TOKEN = "".join(["gh", "p_", "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0"])  # noqa: FLY002


def problems(**layers):
    with pytest.raises(SettingsError) as error:
        resolve_settings(**layers)
    return str(error.value)


def test_a_key_that_is_a_secret_is_never_repeated_in_the_message():
    message = problems(org={GITHUB_TOKEN: 1})

    assert GITHUB_TOKEN not in message
    assert "org settings: a key that looks like a secret is not a setting." in message


def test_a_key_that_is_too_long_or_not_text_is_described_and_not_repeated():
    message = problems(org={"x" * 200: 1, 5: 1})

    assert "x" * 200 not in message
    assert "a key that is too long is not a setting." in message
    assert "a key that is not text is not a setting." in message


def test_the_schema_itself_refuses_a_value_that_looks_like_a_secret():
    with pytest.raises(ValidationError) as error:
        Settings(cheap_model=GITHUB_TOKEN)

    assert GITHUB_TOKEN not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "http://acme.atlassian.net",
        "https://bot:pass@acme.atlassian.net",
        "file:///etc/passwd",
        "https://acme atlassian.net",
    ],
)
def test_the_jira_site_must_be_an_https_address_with_no_password(url):
    assert "jira_site_url" in problems(org={"jira_site_url": url})


def test_an_https_address_is_allowed():
    url = "https://acme.atlassian.net"

    assert resolve_settings(org={"jira_site_url": url}).jira_site_url == url


@pytest.mark.parametrize(
    ("layer", "words"),
    [
        ({"cheap_model": "m" * 101}, "cheap_model is too long."),
        (
            {"jira_project_keys": ["SEC"] * 201},
            "jira_project_keys has too many entries.",
        ),
        (
            {"extra_refused_read_patterns": ["x" * 201]},
            "extra_refused_read_patterns has an entry that is too long.",
        ),
    ],
)
def test_a_value_cannot_be_longer_than_its_bound(layer, words):
    assert words in problems(org=layer)


def test_two_spellings_of_one_severity_word_in_one_layer_are_an_error():
    message = problems(org={"severity_map": {"info": "low", "INFO": "high"}})

    assert "severity_map names a word twice." in message
