"""Wave S2 — fair-share candidate generation caps and distinct-pair dedupe (identity continuity)."""

from __future__ import annotations

from typing import Final

IDENTITY_CONTINUITY_CANDIDATES_SCHEMA_VERSION: Final[int] = 1

RULE_SLACK_USER_ID_V1: Final[str] = "p04.candidate.exact_slack_user_id_v1"
RULE_GITHUB_LOGIN_V1: Final[str] = "p04.candidate.exact_github_login_v1"
RULE_LINEAR_USER_ID_V1: Final[str] = "p04.candidate.exact_linear_user_id_v1"
RULE_NOTION_USER_ID_V1: Final[str] = "p04.candidate.exact_notion_user_id_v1"
RULE_EMAIL_EXACT_V1: Final[str] = "p04.candidate.exact_email_localpart_domain_v1"

# Production continuity rules (plan §5.2) — evaluated before fixture rules.
PROD_CONTINUITY_RULE_IDS: Final[tuple[str, ...]] = (
    RULE_SLACK_USER_ID_V1,
    RULE_GITHUB_LOGIN_V1,
    RULE_LINEAR_USER_ID_V1,
    RULE_NOTION_USER_ID_V1,
    RULE_EMAIL_EXACT_V1,
)

FIXTURE_CONTINUITY_RULE_IDS: Final[frozenset[str]] = frozenset(
    {
        "p04.candidate.email_norm_continuity_evidence_v1",
        "p04.candidate.continuity_fixture_cluster_key_v1",
        "p04.candidate.fixture_declared_link_subject_v1",
        "p04.candidate.fixture_declared_stable_account_key_v1",
    }
)

# Per-rule edge budget so one connector cannot consume the global cap (S2.2).
MAX_CANDIDATE_EDGES_PER_PROD_RULE_V1: Final[int] = 550
MAX_CANDIDATE_EDGES_PER_FIXTURE_RULE_V1: Final[int] = 80

# Wave S2 green: candidate_rows / unique_auth_pairs < 3 when pairs exist.
CANDIDATE_INFLATION_RATIO_GREEN_MAX_V1: Final[float] = 3.0


def max_candidate_edges_for_rule_v1(rule_id: str) -> int:
    rid = (rule_id or "").strip()
    if rid in PROD_CONTINUITY_RULE_IDS:
        return MAX_CANDIDATE_EDGES_PER_PROD_RULE_V1
    if rid in FIXTURE_CONTINUITY_RULE_IDS:
        return MAX_CANDIDATE_EDGES_PER_FIXTURE_RULE_V1
    return MAX_CANDIDATE_EDGES_PER_FIXTURE_RULE_V1


def candidate_endpoint_pair_key_v1(
    *,
    source_entity_id: object,
    target_entity_id: object,
    link_type: str,
) -> tuple[str, str, str]:
    a, b = sorted((str(source_entity_id), str(target_entity_id)))
    return (a, b, (link_type or "").strip())
