"""Phase 04 Step 15 — org-scoped Phase 04 verification slice (P04-15).

Reuses ``run_canonical_verification`` as the single execution engine; filters to ``G-P04-*`` gates
for tenant-scoped audits and optional ``cortex_org_verification_runs`` persistence.

Phase 05 Step **23** optionally attaches the **``org_graph_traversal``** OCTS structural slice +
``octs_slice_hash`` to verification evidence when ``VECTOR_OCTS_TENANT_VERIFICATION_SLICE`` is set
(see ``vector.domains.cortex.traversal.tenant_verification_slice``).

Phase 07 Step **25** optionally attaches the **``org_graph_retrieval``** structural slice +
``retrieval_slice_hash`` when ``VECTOR_RETRIEVAL_TENANT_VERIFICATION_SLICE`` is set
(see ``vector.domains.cortex.retrieval.retrieval_tenant_verification_slice``).
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.verification_engine_metadata import build_verification_engine_pointer_section
from vector.domains.cortex.identity.org_verification_metadata import ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION
from vector.infrastructure.db.models.cortex_org_verification_run import CortexOrgVerificationRun

# Normative numbered policy slots G-P04-01 … G-P04-26 (``phase-04-implementation-plan.md`` §12.1).
PHASE04_NORMATIVE_NUMBERED_GATE_IDS: Final[tuple[str, ...]] = tuple(f"G-P04-{i:02d}" for i in range(1, 27))


def verify_gp04_ver01_phase04_catalog_coherence_static() -> dict[str, Any]:
    """G-P04-VER-01 — normative 01–26 registry tuple + verification metadata lists catalog gate."""
    errors: list[str] = []
    ids = PHASE04_NORMATIVE_NUMBERED_GATE_IDS
    if len(ids) != 26 or len(set(ids)) != 26:
        errors.append("normative_numbered_gate_tuple_invalid")
    ptr = build_verification_engine_pointer_section()
    gate_ids = ptr.get("verification_engine_gate_ids")
    if not isinstance(gate_ids, list):
        errors.append("verification_engine_gate_ids_not_list")
    elif "G-P04-VER-01" not in gate_ids:
        errors.append("metadata_missing_G-P04-VER-01")
    return {
        "id": "G-P04-VER-01",
        "name": "phase04_verification_catalog_coherence",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "normative_numbered_count": len(ids),
            "verification_engine_surface_version": ptr.get("verification_engine_surface_version"),
        },
    }


def phase04_identity_gate_slice(gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gates whose ``id`` is a Phase 04 policy / extension slug (``G-P04-`` prefix)."""
    out: list[dict[str, Any]] = []
    for g in gates:
        gid = str(g.get("id") or "")
        if gid.startswith("G-P04"):
            out.append(g)
    return out


def org_verification_run_public_dict(row: CortexOrgVerificationRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": str(row.tenant_id),
        "engine_schema_version": row.engine_schema_version,
        "passed": row.passed,
        "gates_json": list(row.gates_json),
        "evidence_json": dict(row.evidence_json),
        "created_at": row.created_at,
    }


def run_org_identity_verification(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materialization_sample_limit: int = 50,
    persist: bool = False,
) -> dict[str, Any]:
    """Run full canonical verification, then evaluate PASS on Phase 04 hard_fail gates only."""
    from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification

    full = run_canonical_verification(
        session,
        tenant_id=tenant_id,
        materialization_sample_limit=materialization_sample_limit,
        persist=False,
    )
    p04_gates = phase04_identity_gate_slice(list(full.get("gates") or []))
    p04_passed = all(g.get("passed") for g in p04_gates if g.get("severity") == "hard_fail")
    from vector.domains.cortex.retrieval.retrieval_tenant_verification_slice import (
        build_org_graph_retrieval_verification_slice_v1,
        compute_retrieval_verification_slice_hash_v1,
        retrieval_tenant_verification_slice_enabled_v1,
    )
    from vector.domains.cortex.traversal.tenant_verification_slice import (
        build_org_graph_traversal_verification_slice_v1,
        compute_octs_slice_hash_v1,
        octs_tenant_verification_slice_enabled_v1,
    )

    octs_slice_on = octs_tenant_verification_slice_enabled_v1()
    retrieval_slice_on = retrieval_tenant_verification_slice_enabled_v1()
    evidence: dict[str, Any] = {
        **(full.get("evidence") if isinstance(full.get("evidence"), dict) else {}),
        "canonical_verification_engine_schema_version": full.get("canonical_verification_engine_schema_version"),
        "phase04_gate_count": len(p04_gates),
        "full_verification_gate_count": len(full.get("gates") or []),
        "full_verification_passed": bool(full.get("passed")),
    }

    persisted_run_id: int | None = None
    if persist:
        row = CortexOrgVerificationRun(
            tenant_id=tenant_id,
            engine_schema_version=ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION,
            passed=p04_passed,
            gates_json=p04_gates,
            evidence_json=dict(evidence),
        )
        session.add(row)
        session.flush()
        persisted_run_id = row.id
        if octs_slice_on:
            slice_body = build_org_graph_traversal_verification_slice_v1(
                session, tenant_id=tenant_id, verification_run_id=str(row.id)
            )
            evidence["org_graph_traversal"] = slice_body
            evidence["octs_slice_hash"] = compute_octs_slice_hash_v1(slice_body)
        if retrieval_slice_on:
            rslice = build_org_graph_retrieval_verification_slice_v1(
                session, tenant_id=tenant_id, verification_run_id=str(row.id)
            )
            evidence["org_graph_retrieval"] = rslice
            evidence["retrieval_slice_hash"] = compute_retrieval_verification_slice_hash_v1(rslice)
        if octs_slice_on or retrieval_slice_on:
            row.evidence_json = dict(evidence)
    else:
        if octs_slice_on:
            slice_body = build_org_graph_traversal_verification_slice_v1(
                session, tenant_id=tenant_id, verification_run_id=None
            )
            evidence["org_graph_traversal"] = slice_body
            evidence["octs_slice_hash"] = compute_octs_slice_hash_v1(slice_body)
        if retrieval_slice_on:
            rslice = build_org_graph_retrieval_verification_slice_v1(
                session, tenant_id=tenant_id, verification_run_id=None
            )
            evidence["org_graph_retrieval"] = rslice
            evidence["retrieval_slice_hash"] = compute_retrieval_verification_slice_hash_v1(rslice)

    return {
        "org_identity_verification_engine_schema_version": ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "passed": p04_passed,
        "gates": p04_gates,
        "evidence": evidence,
        "persisted_run_id": persisted_run_id,
    }


def list_org_identity_verification_runs(
    session: Session, *, tenant_id: uuid.UUID, limit: int = 20
) -> list[CortexOrgVerificationRun]:
    lim = max(1, min(int(limit), 100))
    return list(
        session.scalars(
            select(CortexOrgVerificationRun)
            .where(CortexOrgVerificationRun.tenant_id == tenant_id)
            .order_by(CortexOrgVerificationRun.created_at.desc())
            .limit(lim)
        ).all()
    )
