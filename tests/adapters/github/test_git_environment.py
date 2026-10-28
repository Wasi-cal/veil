from pathlib import Path

from pydantic import SecretStr

from tests.adapters.github.support import TOKEN
from veil.adapters.github.git_command import git_environment


def test_git_gets_the_proxy_and_the_certificate_variables_that_it_needs(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.invalid:3128")
    monkeypatch.setenv("SSL_CERT_FILE", "/etc/ssl/corp.pem")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "not-for-git")

    env = git_environment(SecretStr(TOKEN), Path("/tmp/home"))

    assert env["HTTPS_PROXY"] == "http://proxy.example.invalid:3128"
    assert env["SSL_CERT_FILE"] == "/etc/ssl/corp.pem"
    assert "AWS_SECRET_ACCESS_KEY" not in env
