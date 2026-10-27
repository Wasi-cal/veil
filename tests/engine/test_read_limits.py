import pytest

from tests.engine.support import GOOD_EDIT, VULNERABLE, make_context
from tests.fakes import finish, read_file, search
from veil.engine import Settings, run

SECRET = "TOPSECRET-9f3a"


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.local",
        "certs/server.pem",
        "keys/app.key",
        "bundle.p12",
        "id_rsa",
        "keys/id_rsa.pub",
        ".npmrc",
        ".git/config",
        ".ENV",
        "certs/KEY.PEM",
        "ID_RSA",
        ".GIT/config",
        "keys\\id_rsa",
    ],
)
def test_read_file_refuses_secret_paths(tmp_path, path):
    context, _, _, model = make_context(
        tmp_path,
        [[read_file(path)], [GOOD_EDIT], [finish("Fixed.")]],
        files={"app.py": VULNERABLE, path: SECRET},
    )

    run(context)

    assert SECRET not in model.everything_received()


def test_search_skips_secret_files(tmp_path):
    context, _, _, model = make_context(
        tmp_path,
        [[search("value|TOPSECRET")], [GOOD_EDIT], [finish("Fixed.")]],
        files={"app.py": VULNERABLE, ".env": f"KEY={SECRET}\n"},
    )

    run(context)

    result = model.received[1][-1]["content"]
    assert "app.py:3:" in result
    assert SECRET not in model.everything_received()


def test_settings_can_add_refused_patterns_but_not_remove_the_built_in_ones(tmp_path):
    context, _, _, model = make_context(
        tmp_path,
        [
            [read_file("notes.secret")],
            [read_file(".env")],
            [GOOD_EDIT],
            [finish("Fixed.")],
        ],
        files={"app.py": VULNERABLE, "notes.secret": SECRET, ".env": SECRET},
        settings=Settings(extra_refused_read_patterns=("*.secret",)),
    )

    run(context)

    assert SECRET not in model.everything_received()
