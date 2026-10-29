import pytest

from veil.engine import Settings, SettingsError, resolve_settings


def test_the_default_names_are_the_usual_variables():
    settings = Settings()

    assert settings.jira_email_env == "JIRA_EMAIL"
    assert settings.jira_token_env == "JIRA_API_TOKEN"
    assert settings.openai_key_env == "OPENAI_API_KEY"


def test_a_repo_layer_can_name_other_variables():
    settings = resolve_settings(
        repo={
            "jira_email_env": "ACME_JIRA_USER",
            "jira_token_env": "ACME_JIRA_TOKEN",
            "openai_key_env": "ACME_OPENAI_KEY",
        }
    )

    assert settings.jira_token_env == "ACME_JIRA_TOKEN"


@pytest.mark.parametrize("name", ["jira token", "lower_case", "1ABC", "A-B", "", "A=B"])
def test_a_name_that_is_not_a_variable_name_fails(name):
    with pytest.raises(SettingsError) as error:
        resolve_settings(repo={"jira_token_env": name})

    assert "jira_token_env" in str(error.value)
