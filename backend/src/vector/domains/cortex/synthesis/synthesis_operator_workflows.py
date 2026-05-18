"""Phase 08 P08-23 — operator workflows + debugger SPA route law.

Normative: ``DOCS/cortex/synthesis/phase-08-admin-control-plane-spec.md`` §Workflows.
**SYN-WF-01** W1–W4 flows + answerability; **SYN-WF-02** dangerous re-synth gate;
**SYN-WF-03** guided ``SD-*`` remediation links to admin surfaces.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    SYNTHESIS_SD_CODES_REGISTRY_V1,
    build_synthesis_omission_histogram_v1,
)
from vector.domains.cortex.synthesis.synthesis_control_plane import (
    SYNTHESIS_CONTROL_PLANE_SPEC_REF_V1,
    SYNTHESIS_CONTROL_PLANE_SURFACES_V1,
    SYNTHESIS_RBAC_PERMISSION_DANGEROUS_V1,
    SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1,
    list_recent_synthesis_jobs_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import (
    SynthesisOrchestratorError,
    execute_synthesis_job_envelope_v1,
    get_synthesis_job_detail_v1,
)
from vector.infrastructure.db.models.tenant import Tenant

PHASE08_SYNTHESIS_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_WF01_GATE_ID_V1: Final[str] = "G-P08-WF-01"

SYNTHESIS_OPERATOR_WORKFLOWS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-admin-control-plane-spec.md"
)

SYNTHESIS_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1: Final[str] = (
    "DOCS/cortex/10-admin/dangerous-action-safety-model.md"
)

SYN_WF01_RULE_ID_V1: Final[str] = "SYN-WF-01"
SYN_WF02_RULE_ID_V1: Final[str] = "SYN-WF-02"
SYN_WF03_RULE_ID_V1: Final[str] = "SYN-WF-03"

SYNTHESIS_OPERATOR_WORKFLOWS_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "workflow_id": "W1",
        "title": "Debug why is synthesis empty?",
        "steps": "Job debugger → RETRIEVE receipts → SD-* explorer → Phase 07 query debugger",
    },
    {
        "workflow_id": "W2",
        "title": "Verify replay before Phase 09 enablement",
        "steps": "replay_equivalence_synthesis → Replay explorer → S-LEG green → certification",
    },
    {
        "workflow_id": "W3",
        "title": "Force re-synthesis (dangerous)",
        "steps": "tenant + retrieval_lookup_id + epoch pins → RE-SYNTHESIZE {slug}",
    },
    {
        "workflow_id": "W4",
        "title": "Recovery after phase 08 failure",
        "steps": "pipeline phase 08 failed → SD-PIPELINE-GAP vs SD-LLM-* → retry job or re-run phase 07",
    },
)

SYNTHESIS_SURFACE_SPA_ROUTES_V1: Final[dict[str, str]] = {
    "synthesis_health_strip": "",
    "coverage_panel": "coverage",
    "policy_pack_inspector": "policy",
    "job_debugger": "jobs",
    "artifact_explorer": "artifacts",
    "citation_evidence_trace": "citations",
    "synthesis_provenance": "provenance",
    "synthesis_legality_explorer": "legality",
    "synthesis_runtime_legality_matrix": "runtime-legality",
    "synthesis_degradation_explorer": "degradation",
    "synthesis_replay_explorer": "replay",
    "evaluation_explorer": "evaluation",
    "llm_trace_inspector": "llm-trace",
    "pipeline_synthesis_panel": "pipeline",
    "throughput_latency": "observability",
    "certification_view": "certification",
    "control_plane_aggregate": "control-plane",
}

SYNTHESIS_OPERATOR_ANSWERABILITY_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "question": "Why is synthesis empty?",
        "surface_id": "job_debugger",
        "spa_route": "jobs",
    },
    {
        "question": "Which SD code blocked claims?",
        "surface_id": "synthesis_degradation_explorer",
        "spa_route": "degradation",
    },
    {
        "question": "Is synthesis replay-safe?",
        "surface_id": "synthesis_health_strip",
        "spa_route": "",
    },
    {
        "question": "What is publication lag vs retrieval?",
        "surface_id": "coverage_panel",
        "spa_route": "coverage",
    },
    {
        "question": "Did structural twin pass?",
        "surface_id": "synthesis_replay_explorer",
        "spa_route": "replay",
    },
    {
        "question": "What is S-LEG posture?",
        "surface_id": "synthesis_legality_explorer",
        "spa_route": "legality",
    },
)

SYNTHESIS_WORKFLOW_SPA_STEPS_V1: Final[dict[str, list[dict[str, str]]]] = {
    "W1": [
        {"label": "Job debugger", "spa_route": "jobs"},
        {"label": "SD omission explorer", "spa_route": "omissions"},
        {"label": "Degradation topology", "spa_route": "degradation"},
        {
            "label": "Phase 07 query debugger (prefill)",
            "spa_route": "retrieval-query",
            "external_phase": "07",
        },
    ],
    "W2": [
        {"label": "Replay explorer", "spa_route": "replay"},
        {"label": "Legality matrix", "spa_route": "legality"},
        {
            "label": "Run replay_equivalence_synthesis",
            "spa_route": "jobs",
            "workload_class": "replay_equivalence_synthesis",
        },
        {"label": "Certification (Step 30)", "spa_route": "certification"},
    ],
    "W3": [
        {"label": "Dangerous re-synthesize", "spa_route": "resynthesize"},
    ],
    "W4": [
        {"label": "Pipeline synthesis panel", "spa_route": "pipeline"},
        {"label": "Degradation topology", "spa_route": "degradation"},
        {"label": "Retry failed job", "spa_route": "jobs"},
    ],
}

SYNTHESIS_SD_REMEDIATION_LINKS_V1: Final[dict[str, dict[str, str]]] = {
    "SD-CAP-CLAIMS": {
        "spa_route": "policy",
        "hint": "Claim cap exceeded — review policy pack selection caps.",
    },
    "SD-CAP-RETRIEVAL": {
        "spa_route": "policy",
        "hint": "Retrieval sub-query cap exceeded — policy inspector.",
    },
    "SD-CAP-LLM": {
        "spa_route": "llm-trace",
        "hint": "LLM token cap exceeded — model routes + caps.",
    },
    "SD-CITE-GAP": {
        "spa_route": "citations",
        "hint": "Claim omitted — no citable retrieval hit (W1 job debugger).",
    },
    "SD-SCOPE-EMPTY": {
        "spa_route": "jobs",
        "hint": "Empty retrieval scope — job debugger RETRIEVE phase receipts.",
    },
    "SD-UPSTREAM-RD": {
        "spa_route": "retrieval-query",
        "hint": "Upstream RD-* from Phase 07 — open retrieval query debugger.",
        "external_phase": "07",
    },
    "SD-UPSTREAM-LEG": {
        "spa_route": "legality",
        "hint": "Upstream legality floor — synthesis legality explorer.",
    },
    "SD-LLM-TIMEOUT": {
        "spa_route": "llm-trace",
        "hint": "LLM timeout — inspect model route + observability.",
    },
    "SD-LLM-SCHEMA": {
        "spa_route": "llm-trace",
        "hint": "LLM schema validation failed — prompt template + trace.",
    },
    "SD-LLM-POLICY": {
        "spa_route": "policy",
        "hint": "LLM policy rejection — policy pack inspector.",
    },
    "SD-REPLAY-TWIN": {
        "spa_route": "replay",
        "hint": "Structural twin mismatch — replay explorer (W2).",
    },
    "SD-REPLAY-DRIFT": {
        "spa_route": "replay",
        "hint": "Replay drift — replay prove on job.",
    },
    "SD-POLICY-MISMATCH": {
        "spa_route": "policy",
        "hint": "Policy pack digest mismatch — policy inspector.",
    },
    "SD-PUBLISH-BLOCKED": {
        "spa_route": "coverage",
        "hint": "Publication barrier — coverage + publish posture.",
    },
    "SD-PIPELINE-GAP": {
        "spa_route": "pipeline",
        "hint": "Pipeline phase 08 gap — W4 recovery workflow.",
    },
    "SD-TEMPORAL-PIN": {
        "spa_route": "policy",
        "hint": "Temporal pin violation — epoch pins in envelope.",
    },
    "SD-LINEAGE-GAP": {
        "spa_route": "artifacts",
        "hint": "Lineage chain truncated — artifact explorer lineage panel.",
    },
}


class SynthesisOperatorWorkflowsError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def build_synthesis_resynthesize_confirmation_phrase_v1(tenant_slug: str) -> str:
    """W3 confirmation phrase per admin spec."""
    return f"RE-SYNTHESIZE {tenant_slug.strip()}"


def assert_synthesis_resynthesize_confirmation_v1(
    confirmation_phrase: str | None,
    *,
    tenant_slug: str,
) -> None:
    """**SYN-WF-02** — dangerous re-synth requires exact phrase."""
    expected = build_synthesis_resynthesize_confirmation_phrase_v1(tenant_slug)
    if (confirmation_phrase or "").strip() != expected:
        raise SynthesisOperatorWorkflowsError(
            "confirmation_phrase_invalid",
            detail={"expected": expected},
        )


def build_synthesis_spa_route_registry_v1() -> list[dict[str, Any]]:
    """Map sixteen control-plane surfaces to SPA routes (**Step 23 done-when**)."""
    routes: list[dict[str, Any]] = []
    for surface in SYNTHESIS_CONTROL_PLANE_SURFACES_V1:
        sid = str(surface["surface_id"])
        spa = SYNTHESIS_SURFACE_SPA_ROUTES_V1.get(sid, sid.replace("_", "-"))
        routes.append(
            {
                "surface_number": surface["surface_number"],
                "surface_id": sid,
                "label": surface["label"],
                "surface_kind": surface.get("surface_kind"),
                "spa_route": spa,
                "spa_path": (
                    "/admin/tenants/{tenant_id}/cortex/synthesis"
                    if not spa
                    else f"/admin/tenants/{{tenant_id}}/cortex/synthesis/{spa}"
                ),
                "admin_api_routes": list(surface.get("admin_routes") or []),
                "wired": bool(surface.get("wired")),
            }
        )
    routes.append(
        {
            "surface_id": "operator_workflows_hub",
            "label": "Operator workflows",
            "spa_route": "workflows",
            "spa_path": "/admin/tenants/{tenant_id}/cortex/synthesis/workflows",
            "admin_api_routes": ["/workflows"],
            "wired": True,
        }
    )
    routes.append(
        {
            "surface_id": "resynthesize_dangerous",
            "label": "Force re-synthesis (dangerous)",
            "spa_route": "resynthesize",
            "spa_path": "/admin/tenants/{tenant_id}/cortex/synthesis/resynthesize",
            "admin_api_routes": ["/jobs/resynthesize"],
            "wired": True,
            "dangerous": True,
            "permission": SYNTHESIS_RBAC_PERMISSION_DANGEROUS_V1,
            "workflow_id": "W3",
        }
    )
    routes.append(
        {
            "surface_id": "sd_omission_explorer",
            "label": "SD omission explorer",
            "spa_route": "omissions",
            "spa_path": "/admin/tenants/{tenant_id}/cortex/synthesis/omissions",
            "admin_api_routes": ["/omissions"],
            "wired": True,
        }
    )
    return routes


def build_synthesis_operator_workflows_v1() -> list[dict[str, Any]]:
    """W1–W4 with SPA step links."""
    out: list[dict[str, Any]] = []
    for wf in SYNTHESIS_OPERATOR_WORKFLOWS_V1:
        wid = str(wf["workflow_id"])
        out.append(
            {
                **wf,
                "spa_steps": list(SYNTHESIS_WORKFLOW_SPA_STEPS_V1.get(wid, ())),
                "dangerous": wid == "W3",
            }
        )
    return out


def build_synthesis_sd_remediation_links_v1() -> list[dict[str, Any]]:
    """Guided remediation links for every registered ``SD-*`` code."""
    links: list[dict[str, Any]] = []
    for code in sorted(SYNTHESIS_SD_CODES_REGISTRY_V1):
        meta = SYNTHESIS_SD_REMEDIATION_LINKS_V1.get(code, {})
        links.append(
            {
                "synthesis_omission_class": code,
                "sd_code": code,
                "spa_route": meta.get("spa_route", "omissions"),
                "hint": meta.get("hint", "See SD omission explorer and degradation topology."),
                "external_phase": meta.get("external_phase"),
            }
        )
    return links


def list_remediation_links_for_sd_omissions_v1(
    omissions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach guided remediation links to omission rows for job debugger UI."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for om in omissions:
        if not isinstance(om, dict):
            continue
        sd = str(om.get("sd_code") or om.get("synthesis_omission_class") or "")
        if not sd or sd in seen:
            continue
        seen.add(sd)
        meta = SYNTHESIS_SD_REMEDIATION_LINKS_V1.get(sd, {})
        out.append(
            {
                "sd_code": sd,
                "spa_route": meta.get("spa_route", "omissions"),
                "hint": meta.get("hint", ""),
                "external_phase": meta.get("external_phase"),
            }
        )
    return out


def build_retrieval_query_debugger_prefill_v1(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-link Phase 07 query debugger (W1 step 4)."""
    scope = dict(envelope.get("retrieval_scope") or {})
    return {
        "admin_spa_path": "/admin/tenants/{tenant_id}/cortex/retrieval/query",
        "prefill": {
            "retrieval_lookup_id": scope.get("retrieval_lookup_id"),
            "retrieval_query_replay_identity": scope.get("retrieval_query_replay_identity"),
            "execution_partition": envelope.get("execution_partition"),
        },
    }


def list_synthesis_jobs_admin_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
) -> dict[str, Any]:
    """Admin job list for debugger hub."""
    jobs = list_recent_synthesis_jobs_v1(session, tenant_id=tenant_id, limit=limit)
    return {
        "surface_kind": "runtime_backed",
        "tenant_id": str(tenant_id),
        "jobs": jobs,
        "count": len(jobs),
    }


def build_synthesis_omissions_catalog_v1(
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Admin ``GET .../omissions`` — SD histogram + remediation."""
    hist = build_synthesis_omission_histogram_v1()
    return {
        "surface_kind": "derived_aggregate",
        "tenant_id": tenant_id or "",
        "omission_histogram": hist,
        "sd_codes_registry": sorted(SYNTHESIS_SD_CODES_REGISTRY_V1),
        "remediation_links": build_synthesis_sd_remediation_links_v1(),
        "total_omissions": sum(int(v) for v in hist.values()),
    }


def build_synthesis_job_debugger_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> dict[str, Any]:
    """Job debugger surface — detail + remediation + cross-links."""
    detail = get_synthesis_job_detail_v1(session, tenant_id=tenant_id, job_id=job_id)
    receipt = dict(detail.get("synthesis_job_receipt") or {})
    omission_rows = list(receipt.get("synthesis_omission_rows") or [])
    remediation = list_remediation_links_for_sd_omissions_v1(omission_rows)
    envelope = dict(detail.get("envelope_json") or {})
    return {
        "surface_kind": "runtime_backed",
        "debugger_contract": "synthesis_job_debugger_v1",
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "job_detail": detail,
        "synthesis_omission_rows": omission_rows,
        "remediation_links": remediation,
        "retrieval_query_debugger": build_retrieval_query_debugger_prefill_v1(envelope),
        "spa_routes": {
            "replay_inspector": f"/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}/replay-inspector",
            "replay_prove": f"/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}/replay-prove",
            "artifact_list": "/admin/tenants/{tenant_id}/cortex/synthesis/artifacts",
        },
        "operator_workflow_hints": [
            {"workflow_id": "W1", "when": "empty_scope_or_cite_gap"},
            {"workflow_id": "W2", "when": "replay_equivalence_required"},
            {"workflow_id": "W4", "when": "status_failed"},
        ],
    }


def retry_synthesis_job_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> dict[str, Any]:
    """W4 — re-run failed job envelope (sync)."""
    detail = get_synthesis_job_detail_v1(session, tenant_id=tenant_id, job_id=job_id)
    if detail.get("status") not in ("failed", "completed"):
        raise SynthesisOperatorWorkflowsError(
            "job_not_retryable",
            detail={"status": detail.get("status")},
        )
    envelope = dict(detail.get("envelope_json") or {})
    out = execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=envelope)
    return {
        "surface_kind": "runtime_backed",
        "action": "retry",
        "source_job_id": str(job_id),
        "result": out,
    }


def run_dangerous_resynthesize_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    tenant_slug: str,
    confirmation_phrase: str | None,
    body: Mapping[str, Any],
) -> dict[str, Any]:
    """W3 — force re-synthesis with confirmation phrase."""
    assert_synthesis_resynthesize_confirmation_v1(confirmation_phrase, tenant_slug=tenant_slug)
    envelope = dict(body.get("envelope") or body)
    envelope.setdefault("synthesis_intent", "prove")
    envelope.setdefault("execution_partition", "authoritative")
    out = execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=envelope)
    return {
        "surface_kind": "runtime_backed",
        "action": "resynthesize",
        "dangerous": True,
        "permission": SYNTHESIS_RBAC_PERMISSION_DANGEROUS_V1,
        "result": out,
    }


def build_synthesis_operator_workflows_catalog_v1(
    *,
    tenant_id: str | None = None,
    tenant_slug: str | None = None,
) -> dict[str, Any]:
    """Admin ``GET .../workflows`` — workflows, answerability, remediation, SPA registry."""
    registry = build_synthesis_spa_route_registry_v1()
    wired_spa = [r for r in registry if r.get("wired") and r.get("spa_route") is not None]
    slug = tenant_slug or "{tenant_slug}"
    return {
        "synthesis_operator_workflows_runtime_schema_version": (
            PHASE08_SYNTHESIS_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_WF01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_OPERATOR_WORKFLOWS_SPEC_REF_V1,
        "control_plane_spec_ref": SYNTHESIS_CONTROL_PLANE_SPEC_REF_V1,
        "tenant_id": tenant_id,
        "workflows": build_synthesis_operator_workflows_v1(),
        "answerability_table": list(SYNTHESIS_OPERATOR_ANSWERABILITY_V1),
        "remediation_links": build_synthesis_sd_remediation_links_v1(),
        "spa_route_registry": registry,
        "spa_routes_wired_count": len(wired_spa),
        "surfaces_with_spa_routes": len(
            [
                r
                for r in registry
                if r.get("surface_id")
                not in ("operator_workflows_hub", "resynthesize_dangerous", "sd_omission_explorer")
            ]
        ),
        "ui_api_mapping": _build_synthesis_ui_api_mapping_v1(),
        "dangerous_actions": [
            {
                "action_id": "resynthesize",
                "permission": SYNTHESIS_RBAC_PERMISSION_DANGEROUS_V1,
                "confirmation_phrase_template": "RE-SYNTHESIZE {tenant_slug}",
                "confirmation_phrase": build_synthesis_resynthesize_confirmation_phrase_v1(slug),
                "doctrine_ref": SYNTHESIS_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1,
                "spa_route": "resynthesize",
                "workflow_id": "W3",
                "admin_api": "POST .../jobs/resynthesize",
            },
            {
                "action_id": "job_run",
                "permission": SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1,
                "spa_route": "jobs",
                "admin_api": "POST .../jobs/run",
            },
        ],
    }


def _build_synthesis_ui_api_mapping_v1() -> list[dict[str, str]]:
    """SPA route → admin API path template (Step 23 UI ↔ API contract)."""
    return [
        {"spa_route": "", "admin_api": "GET .../overview"},
        {"spa_route": "workflows", "admin_api": "GET .../workflows"},
        {"spa_route": "jobs", "admin_api": "GET .../jobs"},
        {"spa_route": "jobs", "admin_api": "GET .../jobs/{job_id}"},
        {"spa_route": "jobs", "admin_api": "GET .../jobs/{job_id}/debugger"},
        {"spa_route": "jobs", "admin_api": "POST .../jobs/run"},
        {"spa_route": "jobs", "admin_api": "POST .../jobs/{job_id}/retry"},
        {"spa_route": "artifacts", "admin_api": "GET .../artifacts"},
        {"spa_route": "artifacts", "admin_api": "GET .../artifacts/{artifact_id}"},
        {"spa_route": "replay", "admin_api": "GET .../replay-explorer"},
        {"spa_route": "replay", "admin_api": "POST .../jobs/{job_id}/replay-prove"},
        {"spa_route": "degradation", "admin_api": "GET .../degradation-topology"},
        {"spa_route": "omissions", "admin_api": "GET .../omissions"},
        {"spa_route": "legality", "admin_api": "GET .../legality-matrix"},
        {"spa_route": "coverage", "admin_api": "GET .../coverage"},
        {"spa_route": "control-plane", "admin_api": "GET .../control-plane"},
        {"spa_route": "observability", "admin_api": "GET .../observability"},
        {"spa_route": "resynthesize", "admin_api": "POST .../jobs/resynthesize"},
        {"spa_route": "retrieval-query", "admin_api": "GET .../cortex/retrieval/query (Phase 07)"},
    ]


def resolve_tenant_slug_v1(session: Session, *, tenant_id: uuid.UUID) -> str:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise SynthesisOperatorWorkflowsError("tenant_not_found")
    return str(tenant.slug)


def _wf_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_WF01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_wf01_synthesis_spa_routes_complete_static() -> dict[str, Any]:
    """**G-P08-WF-01** — sixteen surfaces have SPA routes; W1–W4 workflows + dangerous gate."""
    errors: list[str] = []
    registry = build_synthesis_spa_route_registry_v1()
    surface_rows = [
        r
        for r in registry
        if r.get("surface_id")
        not in ("operator_workflows_hub", "resynthesize_dangerous", "sd_omission_explorer")
    ]
    if len(surface_rows) != 16:
        errors.append(f"surface_route_count:{len(surface_rows)}")
    for surface in SYNTHESIS_CONTROL_PLANE_SURFACES_V1:
        sid = str(surface["surface_id"])
        if sid not in SYNTHESIS_SURFACE_SPA_ROUTES_V1:
            errors.append(f"missing_spa_map:{sid}")
    if len(SYNTHESIS_OPERATOR_ANSWERABILITY_V1) != 6:
        errors.append("answerability_count")
    if len(SYNTHESIS_OPERATOR_WORKFLOWS_V1) != 4:
        errors.append("workflow_count")
    for code in SYNTHESIS_SD_CODES_REGISTRY_V1:
        if code not in SYNTHESIS_SD_REMEDIATION_LINKS_V1:
            errors.append(f"missing_remediation:{code}")
    try:
        assert_synthesis_resynthesize_confirmation_v1(
            build_synthesis_resynthesize_confirmation_phrase_v1("acme"),
            tenant_slug="acme",
        )
    except SynthesisOperatorWorkflowsError:
        errors.append("confirmation_phrase_should_pass")
    try:
        assert_synthesis_resynthesize_confirmation_v1("wrong", tenant_slug="acme")
        errors.append("confirmation_phrase_should_fail")
    except SynthesisOperatorWorkflowsError:
        pass
    cat = build_synthesis_operator_workflows_catalog_v1()
    if cat["gate_id"] != GP08_WF01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    if len(cat.get("ui_api_mapping") or []) < 10:
        errors.append("ui_api_mapping_sparse")
    return _wf_meta("gp08_wf01_synthesis_spa_routes_complete", errors)
