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
