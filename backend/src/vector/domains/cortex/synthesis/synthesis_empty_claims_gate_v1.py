"""Wave S4 step 19 — Q3: published synthesis artifacts must have ≥1 verifiable claim (fail-loud)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

SYNTHESIS_EMPTY_CLAIMS_GATE_SCHEMA_VERSION: Final[int] = 1
FAILURE_CODE_EMPTY_CLAIMS_V1: Final[str] = "synthesis_empty_claims"
WAVE_S4_STEP_19: Final[str] = "wave_s4_synthesis_empty_claims_gate"

_USEFUL_ARTIFACT_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "execution_brief",
        "island_brief",
        "execution_understanding",
        "execution_narrative",
        "operational_synthesis",
    }
)


class SynthesisEmptyClaimsError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def is_synthesis_empty_claims_gate_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_synthesis_empty_claims_gate_enabled)
    except Exception:  # noqa: BLE001
        return True


def _claim_has_evidence_ref_v1(claim: Mapping[str, Any]) -> bool:
    citations = claim.get("synthesis_citations") or claim.get("citations") or []
    if isinstance(citations, list):
        for cite in citations:
            if not isinstance(cite, Mapping):
                continue
            if str(cite.get("retrieval_lookup_id") or "").strip():
                return True
            refs = cite.get("evidence_refs") or cite.get("evidence_ref_ids") or []
            if isinstance(refs, list) and refs:
                return True
    refs = claim.get("evidence_refs") or claim.get("evidence_ref_ids") or []
    if isinstance(refs, list) and refs:
        return True
    if str(claim.get("retrieval_lookup_id") or "").strip():
        return True
    return False


def count_verifiable_claims_v1(body: Mapping[str, Any] | None) -> int:
    if not isinstance(body, Mapping):
        return 0
    claims = body.get("claims") or []
    if not isinstance(claims, list):
        return 0
    return sum(1 for row in claims if isinstance(row, Mapping) and _claim_has_evidence_ref_v1(row))


def validate_artifact_claims_for_publish_v1(
    *,
    body_json: Mapping[str, Any] | None,
    artifact_kind: str | None = None,
) -> tuple[bool, list[str]]:
    """Return (ok, violations) for publish barrier."""
    body = dict(body_json or {})
    claims = body.get("claims") or []
    if not isinstance(claims, list) or len(claims) == 0:
        return False, ["claims_empty"]
    verifiable = count_verifiable_claims_v1(body)
    if verifiable < 1:
        return False, ["claims_missing_evidence_refs"]
    kind = str(artifact_kind or body.get("artifact_kind") or "").strip()
    if kind == "degradation_brief" and verifiable < 1:
        return False, ["degradation_brief_requires_claim_or_explicit_omission"]
    return True, []


def enforce_empty_claims_before_publish_v1(
    *,
    body_json: Mapping[str, Any] | None,
    artifact_kind: str | None = None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    ok, violations = validate_artifact_claims_for_publish_v1(
        body_json=body_json,
        artifact_kind=artifact_kind,
    )
    audit = {
        "schema_version": SYNTHESIS_EMPTY_CLAIMS_GATE_SCHEMA_VERSION,
        "gate_enabled": is_synthesis_empty_claims_gate_enabled_v1(),
        "ok": ok,
        "violations": violations,
        "claim_count": len((body_json or {}).get("claims") or [])
        if isinstance(body_json, Mapping)
        else 0,
        "verifiable_claim_count": count_verifiable_claims_v1(body_json if isinstance(body_json, Mapping) else {}),
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
    }
    if not ok and is_synthesis_empty_claims_gate_enabled_v1():
        raise SynthesisEmptyClaimsError(
            FAILURE_CODE_EMPTY_CLAIMS_V1,
            detail=audit,
        )
    return audit


def audit_published_artifacts_for_empty_claims_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_ids: Sequence[uuid.UUID],
) -> dict[str, Any]:
    from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact

    violations: list[dict[str, Any]] = []
    checked = 0
    for aid in artifact_ids:
        row = session.get(CortexSynthesisArtifact, aid)
        if row is None or row.tenant_id != tenant_id:
            continue
        checked += 1
        body = dict(row.body_json or {})
        ok, vlist = validate_artifact_claims_for_publish_v1(
            body_json=body,
            artifact_kind=str(row.artifact_kind or ""),
        )
        if not ok:
            violations.append(
                {
                    "artifact_id": str(row.id),
                    "artifact_kind": row.artifact_kind,
                    "violations": vlist,
                }
            )
    return {
        "checked": checked,
        "violation_count": len(violations),
        "violations": violations[:16],
        "ok": len(violations) == 0,
    }
