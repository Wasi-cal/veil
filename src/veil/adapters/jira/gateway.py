from veil.adapters.jira.constants.http import GATEWAY_URL, TENANT_INFO_PATH
from veil.adapters.jira.http_client import JiraHttp
from veil.engine.errors.tracker_error import TrackerError


def resolve_api_base(site_url: str) -> str:
    """The URL that the REST calls go through for a Jira Cloud site. A Shell calls this once.

    A scoped API token works only through the cloud ID gateway. A classic token works through it too.
    """
    reply = JiraHttp(site_url, None).call("GET", TENANT_INFO_PATH, shape=dict)
    cloud_id = reply.get("cloudId")
    if not cloud_id:
        raise TrackerError("The Jira site gave no cloud ID. Check the site URL.")
    return f"{GATEWAY_URL}/{cloud_id}"
