# The names of the lines in the Details list that Gozurion writes in a ticket.
DETAIL_REPOSITORY = "Repository"
DETAIL_COMPONENT = "Component"
DETAIL_LINE = "Line"
DETAIL_SEVERITY = "Severity"
DETAIL_BRANCH = "Branch"
# Gozurion writes this word when the scan knew no branch.
UNKNOWN_BRANCH = "unknown"
# A Sonar component is `project:path`. A plain path has no separator.
COMPONENT_SEPARATOR = ":"

# Gozurion moves these three values into custom fields when a Jira admin makes the fields with these names.
CUSTOM_FIELD_COMPONENT = "SonarQube Component"
CUSTOM_FIELD_LINE = "SonarQube Line"
CUSTOM_FIELD_SEVERITY = "SonarQube Severity"
# The heading above the list of details in a Gozurion description. Only the list below it counts.
DETAILS_HEADING = "Details"
# Gozurion moves each of these details into the custom field with this name.
CUSTOM_FIELD_NAMES = {
    DETAIL_COMPONENT: CUSTOM_FIELD_COMPONENT,
    DETAIL_LINE: CUSTOM_FIELD_LINE,
    DETAIL_SEVERITY: CUSTOM_FIELD_SEVERITY,
}
