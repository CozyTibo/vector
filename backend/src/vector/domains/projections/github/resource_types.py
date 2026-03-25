"""GitHub Step 1 resource_type values consumed by projections."""

RT_REPOSITORY = "github.repository"
RT_PULL_REQUEST = "github.pull_request"
RT_ISSUE = "github.issue"
RT_COMMIT = "github.commit"

GITHUB_RESOURCE_TYPES = frozenset({RT_REPOSITORY, RT_PULL_REQUEST, RT_ISSUE, RT_COMMIT})
