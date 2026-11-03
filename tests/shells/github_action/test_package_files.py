import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / "docs" / "examples" / "veil-action-workflow.yml"


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def triggers(workflow: dict) -> dict:
    # YAML 1.1 reads the key `on` as True.
    return workflow.get("on", workflow.get(True))


def test_the_action_is_one_container_action_from_a_prebuilt_image():
    action = load(ROOT / "action.yml")

    assert action["runs"]["using"] == "docker"
    assert action["runs"]["image"].startswith("docker://ghcr.io/")
    assert (
        "composite" not in str(action["runs"]) and "node" not in action["runs"]["using"]
    )


def test_the_example_workflow_grants_only_two_permissions():
    workflow = load(WORKFLOW)

    assert workflow["permissions"] == {"contents": "write", "pull-requests": "write"}
    for job in workflow["jobs"].values():
        assert "permissions" not in job or job["permissions"] == workflow["permissions"]


def test_the_example_workflow_has_no_pull_request_trigger():
    names = set(triggers(load(WORKFLOW)))

    assert names <= {"schedule", "workflow_dispatch", "repository_dispatch"}
    assert {"schedule", "workflow_dispatch"} <= names


def test_the_example_workflow_allows_one_run_for_each_repo_and_queues_one_more():
    concurrency = load(WORKFLOW)["concurrency"]

    assert concurrency["cancel-in-progress"] is False
    assert "github.repository" in concurrency["group"]


def test_the_example_workflow_checks_out_without_keeping_a_token_and_maps_secrets():
    [job] = load(WORKFLOW)["jobs"].values()
    checkout, action = job["steps"]

    assert checkout["with"]["persist-credentials"] is False
    assert set(action["env"]) >= {
        "GITHUB_TOKEN",
        "JIRA_EMAIL",
        "JIRA_API_TOKEN",
        "OPENAI_API_KEY",
    }
    assert all("secrets." in value for value in action["env"].values())


def test_the_image_installs_nothing_when_it_starts():
    text = (ROOT / "Dockerfile").read_text()

    assert 'ENTRYPOINT ["python", "-m", "veil.shells.github_action.main"]' in text
    assert "--no-dev" in text or "--no-group dev" in text
    lines = [l for l in text.splitlines() if l.startswith(("ENTRYPOINT", "CMD"))]
    assert all("install" not in l and "pip" not in l for l in lines)


# --- the files that the Marketplace listing and the release need ---

RELEASE = ROOT / ".github" / "workflows" / "release-image.yml"
IMAGE = "docker://ghcr.io/wasi-cal/veil:v1"
# The icons and colors that GitHub accepts for the badge of an Action.
ICONS = {"git-pull-request", "shield", "check-circle", "tool", "git-merge"}
COLORS = {"white", "yellow", "blue", "green", "orange", "red", "purple", "gray-dark"}


def test_the_action_has_a_name_that_the_marketplace_can_accept():
    action = load(ROOT / "action.yml")

    # The name must be unique and must not match a GitHub user. A user named veil exists.
    assert action["name"].lower() != "veil"
    assert len(action["name"]) <= 60
    assert len(action["description"]) <= 125
    assert action["author"]


def test_the_action_has_a_badge_that_github_accepts():
    branding = load(ROOT / "action.yml")["branding"]

    assert branding["icon"] in ICONS
    assert branding["color"] in COLORS


def test_the_action_points_at_the_public_image_of_its_owner():
    assert load(ROOT / "action.yml")["runs"]["image"] == IMAGE


def test_the_example_workflow_uses_the_published_action():
    steps = load(WORKFLOW)["jobs"]["veil"]["steps"]

    assert "Wasi-cal/veil@v1" in [step.get("uses") for step in steps]


def test_the_license_keeps_the_rights_of_the_owner():
    text = (ROOT / "LICENSE").read_text()

    assert "All rights reserved" in text
    assert "reverse engineer" in text
    assert not re.search(r"\bMIT\b", text) and "Apache" not in text


def test_calfus_owns_the_code_and_the_listing_says_so():
    license_text = (ROOT / "LICENSE").read_text()

    assert "Copyright (c) 2026 Calfus. All rights reserved." in license_text
    assert "Wasi-cal. All rights" not in license_text
    assert load(ROOT / "action.yml")["author"] == "Calfus"
    assert "Calfus" in (ROOT / "README.md").read_text().split("## License")[1]


def test_the_readme_shows_how_to_use_the_action():
    text = (ROOT / "README.md").read_text()

    assert "Wasi-cal/veil@v1" in text
    for name in ("JIRA_API_TOKEN", "OPENAI_API_KEY", "GITHUB_TOKEN", "JIRA_EMAIL"):
        assert name in text
    assert ".gozu/jira-to-pr.yml" in text


def test_the_release_workflow_runs_only_for_a_version_tag():
    on = triggers(load(RELEASE))

    assert list(on) == ["push"]
    assert on["push"]["tags"] == ["v[0-9]+.[0-9]+.[0-9]+"]
    assert "branches" not in on["push"]


def test_the_release_workflow_tests_first_and_pushes_the_image_with_its_own_token():
    workflow = load(RELEASE)
    text = RELEASE.read_text()

    assert workflow["jobs"]["image"]["needs"] == "test"
    assert workflow["jobs"]["test"]["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["image"]["permissions"] == {
        "contents": "write",
        "packages": "write",
    }
    assert "secrets.GITHUB_TOKEN" in text
    assert text.count("secrets.") == text.count("secrets.GITHUB_TOKEN")
    assert "pull_request" not in text


def test_the_release_workflow_tags_the_image_with_the_version_and_the_major_version():
    text = RELEASE.read_text()

    assert "pattern=v{{version}}" in text
    assert "pattern=v{{major}}" in text


def test_every_action_of_the_release_workflow_is_pinned_to_a_commit():
    uses = re.findall(r"uses:\s*(\S+)", RELEASE.read_text())

    assert uses
    for reference in uses:
        assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", reference), reference


def test_the_base_images_of_the_dockerfile_are_pinned_to_a_digest():
    lines = [
        line
        for line in (ROOT / "Dockerfile").read_text().splitlines()
        if line.startswith("FROM ")
    ]

    assert len(lines) == 2
    for line in lines:
        assert re.search(r"@sha256:[0-9a-f]{64}", line), line


def test_the_release_workflow_tests_on_the_python_of_the_image():
    dockerfile = (ROOT / "Dockerfile").read_text()
    image_python = re.search(r"FROM python:(\d+\.\d+)", dockerfile).group(1)
    steps = load(RELEASE)["jobs"]["test"]["steps"]
    setup = next(step for step in steps if "setup-uv" in step.get("uses", ""))

    assert str(setup["with"]["python-version"]) == image_python
