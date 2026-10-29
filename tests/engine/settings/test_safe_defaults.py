from veil.engine import Settings


def test_the_default_models_are_a_small_one_and_a_mid_tier_one_and_not_the_flagship():
    settings = Settings()

    assert settings.cheap_model == "gpt-6-luna"
    assert settings.strong_model == "gpt-6.1-terra"
    assert "astra" not in settings.cheap_model + settings.strong_model


def test_the_default_budget_and_the_default_rate_are_low():
    settings = Settings()

    assert settings.token_ceiling == 100_000
    assert settings.model_calls_per_minute == 20
    assert settings.max_attempts == 2


def test_the_default_triggers_start_the_fewest_automatic_runs():
    settings = Settings()

    assert settings.schedule_enabled is False
    assert settings.on_demand_enabled is True
    assert settings.event_enabled is True


def test_the_defaults_of_the_service_values_are_the_numbers_of_the_decisions():
    settings = Settings()

    assert settings.quiet_window_minutes == 10
    assert settings.run_timeout_minutes == 60
    assert settings.heartbeat_seconds == 120
    assert settings.max_concurrent_runs == 3
    assert settings.checkout_sweep_minutes == 60
    assert settings.shared_pr_max == 10
    assert settings.read_file_max_lines == 300
    assert settings.search_max_matches == 50
    assert settings.tool_result_max_bytes == 8 * 1024
    assert settings.step_cap == 25
    assert settings.diff_limit == 200
