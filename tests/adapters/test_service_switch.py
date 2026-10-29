import pytest

from tests.adapters.conftest import REQUIRE_VARIABLE, _missing


def test_a_missing_server_skips_the_test_by_default(monkeypatch):
    monkeypatch.delenv(REQUIRE_VARIABLE, raising=False)

    with pytest.raises(pytest.skip.Exception):
        _missing("No server.")


def test_a_missing_server_fails_the_test_when_ci_requires_the_servers(monkeypatch):
    monkeypatch.setenv(REQUIRE_VARIABLE, "1")

    with pytest.raises(pytest.fail.Exception, match="No server"):
        _missing("No server.")
