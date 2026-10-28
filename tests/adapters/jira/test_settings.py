import pytest
from pydantic import ValidationError

from veil.adapters.jira.models.jira_settings import JiraSettings


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
