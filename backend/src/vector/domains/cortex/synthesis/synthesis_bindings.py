"""Phase 08 P08-15 — retrieval/TCRE binding copy on synthesis artifacts (**G-P08-BIND-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md`` §Bindings.
Bindings are **copied** from Phase **07** retrieval ingress — never re-derived.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.phase_boundaries import (
    SD_UPSTREAM_RD_V1,
    map_rd_code_to_sd_code_v1,
    propagate_retrieval_omissions_to_sd_rows_v1,
)
from vector.domains.cortex.synthesis.synthesis_evidence_binding import (
    compute_retrieval_hit_digest_v1,
    normalize_retrieval_hits_v1,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    normalize_retrieval_subquery_replay_identities_v1,
    primary_retrieval_query_replay_identity_v1,
)

PHASE08_SYNTHESIS_BINDINGS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_BIND01_GATE_ID_V1: Final[str] = "G-P08-BIND-01"

SYNTHESIS_BINDINGS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md"
)

SYN_BND_07_02_RULE_ID_V1: Final[str] = "SYN-BND-07-02"

_TCRE_BIND_FAILURE_STATES_V1: Final[frozenset[str]] = frozenset(
    {"failed", "blocked", "orphan", "candidate_only"},
)


class SynthesisBindingsError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        http_status: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


def _shallow_copy_mapping_v1(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(k): v for k, v in value.items()}


def _sd_code_from_synthesis_row(row: Mapping[str, Any]) -> str:
    return str(row.get("sd_code") or row.get("synthesis_omission_class") or "").strip()


def _ingress_legality_field_v1(retrieval_ingress: Mapping[str, Any], field: str) -> str:
    """Read legality from ingress ``retrieval_legality_copy`` or top-level copy."""
    leg_copy = retrieval_ingress.get("retrieval_legality_copy")
    if isinstance(leg_copy, Mapping):
        val = leg_copy.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip()
    direct = retrieval_ingress.get(field)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    return ""


def _passthrough_retrieval_binding_fields_v1(
    retrieval_ingress: dict[str, Any],
    retrieval_response: Mapping[str, Any] | None,
) -> None:
    """Merge Phase **07** binding envelopes from raw retrieval response into ingress snapshot."""
    if not isinstance(retrieval_response, Mapping):
        return
    for key in (
        "tcre_binding_envelope",
        "tcre_replay_artifact_pins",
        "traversal_binding_envelope",
        "graph_binding_envelope",
        "lineage_binding_envelope",
        "lineage_chain_digest",
        "retrieval_query_receipt",
    ):
        if key in retrieval_response and key not in retrieval_ingress:
            retrieval_ingress[key] = retrieval_response[key]


def collect_retrieval_evidence_hit_digests_v1(
    retrieval_ingress: Mapping[str, Any],
) -> list[str]:
    hits = normalize_retrieval_hits_v1(retrieval_ingress)
    digests = [compute_retrieval_hit_digest_v1(hit) for hit in hits]
    return sorted({d for d in digests if d})


def build_retrieval_binding_envelope_v1(
    *,
    retrieval_ingress: Mapping[str, Any],
    retrieval_subqueries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Copy retrieval replay pins + legality classes (**SYN-BND-07-02** / **SYN-BND-07-03**)."""
    receipt = retrieval_ingress.get("retrieval_query_receipt")
    receipt_digest = str(retrieval_ingress.get("retrieval_query_receipt_digest") or "")
    if isinstance(receipt, Mapping):
        receipt_digest = receipt_digest or str(receipt.get("receipt_digest") or "")
    return {
        "schema_version": 1,
        "copy_law": SYN_BND_07_02_RULE_ID_V1,
        PHASE07_REPLAY_IDENTITY_FIELD_V1: primary_retrieval_query_replay_identity_v1(
            retrieval_subqueries,
            retrieval_ingress=retrieval_ingress,
        ),
        "retrieval_ingress_digest": str(retrieval_ingress.get("retrieval_ingress_digest") or ""),
        "retrieval_subquery_replay_identities": normalize_retrieval_subquery_replay_identities_v1(
            retrieval_subqueries,
        ),
        "retrieval_evidence_hit_digests": collect_retrieval_evidence_hit_digests_v1(
            retrieval_ingress,
        ),
        "retrieval_legality_class": _ingress_legality_field_v1(
            retrieval_ingress,
            "retrieval_legality_class",
        ),
        "chronology_legality_class": _ingress_legality_field_v1(
            retrieval_ingress,
            "chronology_legality_class",
        ),
        "causal_legality_class": _ingress_legality_field_v1(
            retrieval_ingress,
            "causal_legality_class",
        ),
        "retrieval_query_receipt_digest": receipt_digest,
        "retrieval_policy_pack_digest": str(
            retrieval_ingress.get("retrieval_policy_pack_digest") or "",
        ),
    }


def copy_tcre_binding_envelope_v1(retrieval_ingress: Mapping[str, Any]) -> dict[str, Any]:
    """Shallow copy of Phase **07** ``tcre_binding_envelope`` — no TCRE re-derive."""
    src = retrieval_ingress.get("tcre_binding_envelope")
    if isinstance(src, Mapping) and src:
        return _shallow_copy_mapping_v1(src)
    out: dict[str, Any] = {"schema_version": 1, "bind_state": "idle", "copy_source": "synthesis_bindings_empty"}
    pins = retrieval_ingress.get("tcre_replay_artifact_pins")
    if isinstance(pins, list) and pins:
        out["replay_artifact_pins"] = [
            dict(p) if isinstance(p, Mapping) else p for p in pins if p is not None
        ]
    return out


def build_degradation_propagation_chain_v1(
    *,
    retrieval_ingress: Mapping[str, Any],
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """RD→SD propagation chain copied onto artifact (explainability)."""
    chain: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    rd_rows = list(retrieval_ingress.get("retrieval_omission_rows") or [])
    if not rd_rows:
        rd_rows = list(retrieval_ingress.get("omissions") or [])
    for row in rd_rows:
        if not isinstance(row, Mapping):
            continue
        rd_code = str(row.get("retrieval_omission_class") or row.get("rd_code") or "").strip()
        if not rd_code:
            continue
        sd_code = map_rd_code_to_sd_code_v1(rd_code)
        key = (rd_code, sd_code)
        if key in seen:
            continue
        seen.add(key)
        chain.append(
            {
                "rd_code": rd_code,
                "sd_code": sd_code,
                "propagation": "retrieval_to_synthesis",
                "source": "retrieval_ingress",
            },
        )
    for row in synthesis_omission_rows:
        if not isinstance(row, Mapping):
            continue
        sd_code = _sd_code_from_synthesis_row(row)
        rd_code = str(row.get("upstream_rd") or row.get("detail", {}).get("rd_code") or "")
        if isinstance(row.get("detail"), Mapping):
            rd_code = rd_code or str(row["detail"].get("rd_code") or "")
        key = (rd_code or "*", sd_code)
        if key in seen or not sd_code:
            continue
        seen.add(key)
        chain.append(
            {
                "rd_code": rd_code or None,
                "sd_code": sd_code,
                "propagation": "synthesis_omission_row",
                "source": "synthesis_taxonomy",
            },
        )
    return sorted(chain, key=lambda x: (str(x.get("sd_code")), str(x.get("rd_code"))))


def list_tcre_binding_gap_sd_rows_v1(
    tcre_binding_envelope: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Emit **SD-UPSTREAM-RD** when upstream TCRE bind did not succeed."""
    state = str(tcre_binding_envelope.get("bind_state") or "").strip().lower()
    if state and state not in _TCRE_BIND_FAILURE_STATES_V1:
        return []
    if state == "idle" and not tcre_binding_envelope.get("replay_artifact_pins"):
        return []
    detail: dict[str, Any] = {"bind_state": state or "missing"}
    if tcre_binding_envelope.get("tcre_reconstruction_job_id"):
        detail["tcre_reconstruction_job_id"] = tcre_binding_envelope["tcre_reconstruction_job_id"]
    return [
        {
            "sd_code": SD_UPSTREAM_RD_V1,
            "synthesis_omission_class": SD_UPSTREAM_RD_V1,
            "omission_semantics": "omitted_upstream",
            "upstream_rd": "RD-TCRE-GAP",
            "detail": detail,
        },
    ]


def build_synthesis_binding_bundle_v1(
    *,
    retrieval_ingress: Mapping[str, Any],
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    synthesis_omission_rows: Sequence[Mapping[str, Any]] | None = None,
    retrieval_response_source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Binding fields merged into ``SynthesisIntelligenceArtifactV1`` before digest."""
    ingress_mutable = dict(retrieval_ingress)
    _passthrough_retrieval_binding_fields_v1(ingress_mutable, retrieval_response_source)
    tcre = copy_tcre_binding_envelope_v1(ingress_mutable)
    omissions = list(synthesis_omission_rows or [])
    gap_rows = list_tcre_binding_gap_sd_rows_v1(tcre)
    return {
        "retrieval_binding_envelope": build_retrieval_binding_envelope_v1(
            retrieval_ingress=ingress_mutable,
            retrieval_subqueries=retrieval_subqueries,
        ),
        "tcre_binding_envelope": tcre,
        "degradation_propagation_chain": build_degradation_propagation_chain_v1(
            retrieval_ingress=ingress_mutable,
            synthesis_omission_rows=omissions,
        ),
        "binding_gap_sd_rows": gap_rows,
    }


def list_synthesis_binding_copy_violations_v1(
    retrieval_ingress: Mapping[str, Any],
    *,
    retrieval_binding_envelope: Mapping[str, Any],
    tcre_binding_envelope: Mapping[str, Any],
) -> list[str]:
    """Verify legality classes were copied, not upgraded."""
    violations: list[str] = []
    upstream_leg = _ingress_legality_field_v1(retrieval_ingress, "retrieval_legality_class")
    copied_leg = str(retrieval_binding_envelope.get("retrieval_legality_class") or "")
    if upstream_leg and copied_leg and upstream_leg != copied_leg:
        violations.append("retrieval_legality_class_mutated")
    src = retrieval_ingress.get("tcre_binding_envelope")
    if isinstance(src, Mapping) and src:
        if str(src.get("bind_state") or "") != str(tcre_binding_envelope.get("bind_state") or ""):
            violations.append("tcre_bind_state_mutated")
    return violations


def enforce_synthesis_binding_copy_law_v1(
    retrieval_ingress: Mapping[str, Any],
    *,
    retrieval_binding_envelope: Mapping[str, Any],
    tcre_binding_envelope: Mapping[str, Any],
) -> None:
    violations = list_synthesis_binding_copy_violations_v1(
        retrieval_ingress,
        retrieval_binding_envelope=retrieval_binding_envelope,
        tcre_binding_envelope=tcre_binding_envelope,
    )
    if violations:
        raise SynthesisBindingsError(
            "synthesis_binding_copy_law_violation",
            detail={"violations": violations},
        )


def build_synthesis_binding_panel_v1(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Admin binding panel — claims, legality, publication + binding envelopes."""
    rb = artifact.get("retrieval_binding_envelope")
    tb = artifact.get("tcre_binding_envelope")
    chain = artifact.get("degradation_propagation_chain")
    return {
        "surface_kind": "synthesis_binding_panel",
        "phase08_synthesis_bindings_runtime_schema_version": (
            PHASE08_SYNTHESIS_BINDINGS_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_BIND01_GATE_ID_V1,
        "artifact_id": artifact.get("artifact_id"),
        "artifact_digest": artifact.get("artifact_digest"),
        "synthesis_legality_class": artifact.get("synthesis_legality_class"),
        "published": False,
        "synthesis_publication_epoch": artifact.get("synthesis_publication_epoch"),
        "retrieval_binding_envelope": dict(rb) if isinstance(rb, Mapping) else {},
        "tcre_binding_envelope": dict(tb) if isinstance(tb, Mapping) else {},
        "degradation_propagation_chain": list(chain) if isinstance(chain, list) else [],
        "propagation_row_count": len(chain) if isinstance(chain, list) else 0,
        "hit_digest_count": len(
            (rb or {}).get("retrieval_evidence_hit_digests", [])
            if isinstance(rb, Mapping)
            else [],
        ),
    }


def build_synthesis_bindings_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_bindings_law_v1",
        "phase08_synthesis_bindings_runtime_schema_version": (
            PHASE08_SYNTHESIS_BINDINGS_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_BIND01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_BINDINGS_SPEC_REF_V1,
        "rules": [
            {"id": "SYN-BND-07-02", "text": "Copy retrieval legality classes — never upgrade via LLM"},
            {"id": "SYN-BND-07-03", "text": "Pin retrieval_query_replay_identity on artifact header"},
            {"id": "G-P08-BIND-01", "text": "Bindings copied only — no re-derive"},
        ],
        "artifact_binding_fields": [
            "retrieval_binding_envelope",
            "tcre_binding_envelope",
            "degradation_propagation_chain",
        ],
        "sd_upstream_binding_gap": SD_UPSTREAM_RD_V1,
    }


def verify_gp08_bind01_copy_only_static() -> dict[str, Any]:
    errors: list[str] = []
    ingress: dict[str, Any] = {
        "retrieval_legality_class": "retrieval_degraded",
        "chronology_legality_class": "chronology_bounded",
        "causal_legality_class": "causal_partial",
        "retrieval_policy_pack_digest": "sha256:" + "c" * 64,
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:bind-static",
        "retrieval_omission_rows": [
            {"retrieval_omission_class": "RD-TCRE-GAP", "detail": {}},
        ],
        "tcre_binding_envelope": {
            "bind_state": "failed",
            "schema_version": 1,
        },
        "retrieval_evidence_hits": [],
    }
    sub: list[dict[str, Any]] = [
        {PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:bind-static"},
    ]
    b1 = build_synthesis_binding_bundle_v1(
        retrieval_ingress=ingress,
        retrieval_subqueries=sub,
        synthesis_omission_rows=propagate_retrieval_omissions_to_sd_rows_v1(
            ingress["retrieval_omission_rows"],
        ),
    )
    b2 = build_synthesis_binding_bundle_v1(
        retrieval_ingress=ingress,
        retrieval_subqueries=sub,
        synthesis_omission_rows=propagate_retrieval_omissions_to_sd_rows_v1(
            ingress["retrieval_omission_rows"],
        ),
    )
    if b1 != b2:
        errors.append("binding_bundle_not_deterministic")
    try:
        enforce_synthesis_binding_copy_law_v1(
            ingress,
            retrieval_binding_envelope=b1["retrieval_binding_envelope"],
            tcre_binding_envelope=b1["tcre_binding_envelope"],
        )
    except SynthesisBindingsError as exc:
        errors.append(f"unexpected_copy_law_failure:{exc}")
    gap = list_tcre_binding_gap_sd_rows_v1(b1["tcre_binding_envelope"])
    if not gap or gap[0].get("sd_code") != SD_UPSTREAM_RD_V1:
        errors.append("expected_sd_upstream_rd_on_tcre_bind_failure")
    chain = b1.get("degradation_propagation_chain") or []
    if not any(row.get("rd_code") == "RD-TCRE-GAP" for row in chain if isinstance(row, Mapping)):
        errors.append("expected_rd_tcre_gap_in_propagation_chain")
    return {
        "id": GP08_BIND01_GATE_ID_V1,
        "name": "synthesis_binding_copy_only",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
