"""Linear Step 1 resource_type strings — keep in sync with `linear_graphql_sync`."""

RT_VIEWER = "linear.viewer"
RT_TEAM = "linear.team"
RT_USER = "linear.user"
RT_WORKFLOW_STATE = "linear.workflow_state"
RT_PROJECT = "linear.project"
RT_ISSUE = "linear.issue"
RT_COMMENT = "linear.comment"
RT_ISSUE_RELATION = "linear.issue_relation"
RT_ISSUE_LABEL = "linear.issue_label"
RT_CYCLE = "linear.cycle"
RT_INITIATIVE = "linear.initiative"

LINEAR_RESOURCE_TYPES = frozenset(
    {
        RT_VIEWER,
        RT_TEAM,
        RT_USER,
        RT_WORKFLOW_STATE,
        RT_PROJECT,
        RT_INITIATIVE,
        RT_CYCLE,
        RT_ISSUE_LABEL,
        RT_ISSUE,
        RT_COMMENT,
        RT_ISSUE_RELATION,
    },
)
