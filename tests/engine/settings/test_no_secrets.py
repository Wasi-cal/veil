import pytest

from veil.engine import SettingsError, resolve_settings

GITHUB_TOKEN = "".join(["gh", "p_", "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0"])  # noqa: FLY002


@pytest.mark.parametrize("layer", ["org", "repo", "overrides"])
def test_a_value_that_looks_like_a_secret_is_refused_in_every_layer(layer):
    with pytest.raises(SettingsError) as error:
        resolve_settings(**{layer: {"cheap_model": GITHUB_TOKEN}})

    message = str(error.value)
    assert (
        "cheap_model holds text that looks like a secret (a GitHub token)." in message
    )
    assert "Settings hold no secrets." in message
    assert GITHUB_TOKEN not in message


def test_a_secret_inside_a_list_or_an_address_is_refused_too():
    with pytest.raises(SettingsError) as error:
        resolve_settings(
            org={
                "extra_refused_read_patterns": ["*.pem", GITHUB_TOKEN],
                "jira_site_url": f"https://bot:{GITHUB_TOKEN}@example.atlassian.net",
            }
        )

    lines = str(error.value).splitlines()
    assert len(lines) == 2
    assert all(GITHUB_TOKEN not in line for line in lines)


def test_text_that_only_looks_a_little_like_a_key_is_allowed():
    settings = resolve_settings(
        org={"cheap_model": "gpt-6-luna", "branch_prefix": "gh/p-"}
    )

    assert settings.cheap_model == "gpt-6-luna"
