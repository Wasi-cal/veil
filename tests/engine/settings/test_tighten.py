import pytest

from veil.engine import SettingsError, resolve_settings


def fails(repo, org, words):
    with pytest.raises(SettingsError) as error:
        resolve_settings(org=org, repo=repo)
    assert f"repo settings: {words}" in str(error.value)


def test_a_repo_may_lower_a_limit_or_keep_it():
    assert resolve_settings(org={"step_cap": 20}, repo={"step_cap": 15}).step_cap == 15
    assert resolve_settings(org={"step_cap": 20}, repo={"step_cap": 20}).step_cap == 20


def test_a_repo_may_not_raise_a_limit_past_the_org_value():
    fails(
        repo={"step_cap": 25},
        org={"step_cap": 20},
        words="step_cap is higher than the org value. A repo can only lower it.",
    )


def test_with_no_org_value_a_repo_may_set_any_value_inside_the_bounds():
    assert resolve_settings(repo={"step_cap": 60}).step_cap == 60


def test_a_run_override_is_not_held_to_the_org_value():
    settings = resolve_settings(
        org={"step_cap": 20}, repo={"step_cap": 15}, overrides={"step_cap": 30}
    )

    assert settings.step_cap == 30


def test_a_repo_may_add_refused_read_patterns_but_not_drop_one():
    org = {"extra_refused_read_patterns": ["*.secret"]}

    ok = resolve_settings(
        org=org, repo={"extra_refused_read_patterns": ["*.secret", "*.cfg"]}
    )

    assert ok.extra_refused_read_patterns == ("*.secret", "*.cfg")
    fails(
        repo={"extra_refused_read_patterns": ["*.cfg"]},
        org=org,
        words="extra_refused_read_patterns drops a pattern of the org. A repo can only add patterns.",
    )


def test_a_repo_may_raise_a_severity_bucket_but_not_lower_one():
    org = {"severity_map": {"INFO": "medium"}}

    ok = resolve_settings(org=org, repo={"severity_map": {"INFO": "high"}})

    assert ok.severity_map["INFO"] == "high"
    fails(
        repo={"severity_map": {"INFO": "low"}},
        org=org,
        words="severity_map lowers a bucket. A repo can only raise a bucket.",
    )


def test_a_repo_may_not_lower_a_default_word_that_the_org_changed_by_leaving_it():
    fails(
        repo={"severity_map": {"BLOCKER": "low"}},
        org={"severity_map": {"INFO": "low"}},
        words="severity_map lowers a bucket. A repo can only raise a bucket.",
    )


def test_a_repo_may_turn_a_trigger_off_but_not_on():
    assert not resolve_settings(
        org={"schedule_enabled": True}, repo={"schedule_enabled": False}
    ).schedule_enabled
    fails(
        repo={"schedule_enabled": True},
        org={"schedule_enabled": False},
        words="schedule_enabled is off in the org. A repo can only turn it off.",
    )


def test_a_repo_may_not_change_a_value_that_the_org_locks():
    fails(
        repo={"branch_prefix": "repo/fix-"},
        org={"branch_prefix": "org/fix-"},
        words="branch_prefix is set by the org. A repo cannot change it.",
    )
    same = resolve_settings(
        org={"branch_prefix": "org/fix-"}, repo={"branch_prefix": "org/fix-"}
    )
    assert same.branch_prefix == "org/fix-"


@pytest.mark.parametrize(
    "key", ["cheap_model", "strong_model", "eligible_label", "failed_fix_label"]
)
def test_a_repo_may_pick_its_own_models_and_labels(key):
    settings = resolve_settings(org={key: "org-value"}, repo={key: "repo-value"})

    assert getattr(settings, key) == "repo-value"


def test_every_problem_of_a_repo_is_listed_together():
    with pytest.raises(SettingsError) as error:
        resolve_settings(
            org={"step_cap": 10, "branch_prefix": "org/fix-"},
            repo={"step_cap": 20, "branch_prefix": "repo/fix-"},
        )

    assert len(str(error.value).splitlines()) == 2
