import pytest
from pydantic import ValidationError

from veil.adapters.jira.models.jira_settings import JiraSettings
from veil.engine import Settings, SettingsError


@pytest.mark.parametrize("keys", [('SEC") OR ("',), ("sec",), ()])
def test_the_settings_refuse_a_project_key_that_could_change_the_search(keys):
    with pytest.raises(ValidationError):
        JiraSettings(site_url="https://x.atlassian.net", project_keys=keys)


@pytest.mark.parametrize("label", ['a" OR labels = "b', "two words", "", "back\\slash"])
def test_the_settings_refuse_an_eligible_label_that_could_change_the_search(label):
    with pytest.raises(ValidationError):
        JiraSettings(
            site_url="https://x.atlassian.net",
            project_keys=("SEC",),
            eligible_label=label,
        )


def test_the_jira_settings_come_from_the_settings_of_the_run():
    settings = Settings(
        jira_site_url="https://acme.atlassian.net",
        jira_project_keys=("SEC", "OPS"),
        eligible_label="fix-me",
    )

    jira = JiraSettings.from_settings(settings)

    assert jira.site_url == "https://acme.atlassian.net"
    assert jira.project_keys == ("SEC", "OPS")
    assert jira.eligible_label == "fix-me"


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"jira_site_url": "https://acme.atlassian.net"},
        {"jira_project_keys": ("SEC",)},
    ],
    ids=["nothing", "no project keys", "no site"],
)
def test_a_run_for_jira_needs_a_site_and_project_keys(fields):
    with pytest.raises(SettingsError) as error:
        JiraSettings.from_settings(Settings(**fields))

    assert "jira" in str(error.value)
