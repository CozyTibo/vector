"""Phase 08 P08-16 — synthesis artifact lineage (**G-P08-LIN-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md`` §Lineage.
Reuses Phase **07** ``build_artifact_lineage_chain_v1`` + ``cortex_artifact_lineage_edges``.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.artifact_lineage_graph import persist_lineage_edge_v1
from vector.domains.cortex.lineage.lineage_chain_builder import build_artifact_lineage_chain_v1
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_artifact_lineage import (
    RETRIEVAL_RD_LINEAGE_GAP_V1,
    compute_lineage_coverage_v1,
    detect_lineage_chain_truncated_v1,
    validate_lineage_chain_replay_pin_v1,
)
from vector.domains.cortex.synthesis.synthesis_evidence_binding import normalize_retrieval_hits_v1
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    primary_retrieval_query_replay_identity_v1,
)

PHASE08_SYNTHESIS_LINEAGE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_LIN01_GATE_ID_V1: Final[str] = "G-P08-LIN-01"

SYNTHESIS_LINEAGE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md"
)

SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1: Final[str] = "synthesis_intelligence"

SYNTHESIS_EDGE_DERIVED_FROM_V1: Final[str] = "synthesis_derived_from"
SYNTHESIS_EDGE_INDEXES_V1: Final[str] = "synthesis_indexes"
SYNTHESIS_EDGE_USES_V1: Final[str] = "synthesis_uses"

SD_LINEAGE_GAP_V1: Final[str] = "SD-LINEAGE-GAP"

SYNTHESIS_DEFAULT_MAX_LINEAGE_HOPS_V1: Final[int] = 32


class SynthesisLineageError(ValueError):
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


def effective_max_lineage_hops_v1(
    envelope: Mapping[str, Any] | None = None,
) -> int:
    selection = (envelope or {}).get("selection_policy")
    if isinstance(selection, Mapping):
        raw = selection.get("max_lineage_hops")
        if raw is not None:
            return max(1, min(int(raw), 256))
    pack = load_synthesis_policy_pack_v1()
    caps = pack.get("caps") if isinstance(pack.get("caps"), Mapping) else {}
    if isinstance(caps, Mapping) and caps.get("max_lineage_hops") is not None:
        return max(1, min(int(caps["max_lineage_hops"]), 256))
    return SYNTHESIS_DEFAULT_MAX_LINEAGE_HOPS_V1


def _retrieval_receipt_ref_v1(
    *,
    retrieval_ingress: Mapping[str, Any],
    retrieval_subqueries: Sequence[Mapping[str, Any]],
) -> str:
    rqid = primary_retrieval_query_replay_identity_v1(
        retrieval_subqueries,
        retrieval_ingress=retrieval_ingress,
    )
    if rqid:
        return rqid
    digest = str(retrieval_ingress.get("retrieval_query_receipt_digest") or "")
    if digest:
        return digest
    receipt = retrieval_ingress.get("retrieval_query_receipt")
    if isinstance(receipt, Mapping):
        return str(receipt.get("receipt_digest") or "retrieval_query_receipt")
    return "retrieval_query_receipt"


def persist_synthesis_artifact_lineage_edges_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_id: str,
    retrieval_ingress: Mapping[str, Any],
    retrieval_subqueries: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Persist terminal→upstream edges for a synthesis artifact (doctrine §Lineage)."""
    persisted_kinds: list[str] = []
    rqid = primary_retrieval_query_replay_identity_v1(
        retrieval_subqueries,
        retrieval_ingress=retrieval_ingress,
    )
    receipt_ref = _retrieval_receipt_ref_v1(
        retrieval_ingress=retrieval_ingress,
        retrieval_subqueries=retrieval_subqueries,
    )
    persist_lineage_edge_v1(
        session,
        tenant_id=tenant_id,
        from_artifact_kind="retrieval_query_receipt",
        from_artifact_ref=receipt_ref,
        to_artifact_kind=SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1,
        to_artifact_ref=artifact_id,
        edge_kind=SYNTHESIS_EDGE_DERIVED_FROM_V1,
        replay_identity=rqid or None,
    )
    persisted_kinds.append(SYNTHESIS_EDGE_DERIVED_FROM_V1)

    seen_lookups: set[str] = set()
    for hit in normalize_retrieval_hits_v1(retrieval_ingress):
        lookup_id = str(hit.get("retrieval_lookup_id") or "").strip()
        if not lookup_id or lookup_id in seen_lookups:
            continue
        seen_lookups.add(lookup_id)
        persist_lineage_edge_v1(
            session,
            tenant_id=tenant_id,
            from_artifact_kind="retrieval_index",
            from_artifact_ref=lookup_id,
            to_artifact_kind=SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1,
            to_artifact_ref=artifact_id,
            edge_kind=SYNTHESIS_EDGE_INDEXES_V1,
            replay_identity=rqid or None,
        )
        if SYNTHESIS_EDGE_INDEXES_V1 not in persisted_kinds:
            persisted_kinds.append(SYNTHESIS_EDGE_INDEXES_V1)

    tcre = retrieval_ingress.get("tcre_binding_envelope")
    if isinstance(tcre, Mapping):
        pins = tcre.get("replay_artifact_pins")
        if isinstance(pins, list):
            for pin in pins:
                if not isinstance(pin, Mapping):
                    continue
                kind = str(pin.get("artifact_kind") or pin.get("kind") or "").strip()
                ref = str(pin.get("artifact_ref") or pin.get("ref") or "").strip()
                if kind and ref:
                    persist_lineage_edge_v1(
                        session,
                        tenant_id=tenant_id,
                        from_artifact_kind=kind,
                        from_artifact_ref=ref,
                        to_artifact_kind=SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1,
                        to_artifact_ref=artifact_id,
                        edge_kind=SYNTHESIS_EDGE_USES_V1,
                        replay_identity=str(pin.get("replay_identity") or rqid or "") or None,
                    )
                    if SYNTHESIS_EDGE_USES_V1 not in persisted_kinds:
                        persisted_kinds.append(SYNTHESIS_EDGE_USES_V1)

    for hit in normalize_retrieval_hits_v1(retrieval_ingress):
        artifact_ref = hit.get("artifact_ref_json")
        if not isinstance(artifact_ref, Mapping):
            continue
        for ref_key, kind in (
            ("causal_chain_id", "tcre_chain"),
            ("walk_id", "octs_walk"),
            ("lineage_id", "lineage"),
        ):
            ref_val = str(artifact_ref.get(ref_key) or "").strip()
            if not ref_val:
                continue
            persist_lineage_edge_v1(
                session,
                tenant_id=tenant_id,
                from_artifact_kind=kind,
                from_artifact_ref=ref_val,
                to_artifact_kind=SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1,
                to_artifact_ref=artifact_id,
                edge_kind=SYNTHESIS_EDGE_USES_V1,
                replay_identity=rqid or None,
            )
            if SYNTHESIS_EDGE_USES_V1 not in persisted_kinds:
                persisted_kinds.append(SYNTHESIS_EDGE_USES_V1)
    return persisted_kinds


def build_synthesis_artifact_lineage_chain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_id: str,
    max_hops: int | None = None,
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Terminal→root chain with ``synthesis_intelligence`` terminal (**RET-LINEAGE-01**)."""
    cap = max_hops if max_hops is not None else effective_max_lineage_hops_v1(envelope)
    return build_artifact_lineage_chain_v1(
        session,
        tenant_id=tenant_id,
        terminal_artifact_kind=SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1,
        terminal_artifact_ref=artifact_id,
        max_hops=cap,
    )


def list_synthesis_lineage_gap_sd_rows_v1(
    *,
    truncated: bool,
    pin_mismatch: bool = False,
) -> list[dict[str, Any]]:
    if not truncated and not pin_mismatch:
        return []
    detail: dict[str, Any] = {}
    if truncated:
        detail["reason"] = "max_lineage_hops_truncated"
    if pin_mismatch:
        detail["reason"] = "lineage_chain_digest_mismatch"
    return [
        {
            "sd_code": SD_LINEAGE_GAP_V1,
            "synthesis_omission_class": SD_LINEAGE_GAP_V1,
            "omission_semantics": "omitted_lineage",
            "upstream_rd": RETRIEVAL_RD_LINEAGE_GAP_V1,
            "detail": detail,
        },
    ]


def apply_synthesis_lineage_to_artifact_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_body: dict[str, Any],
    retrieval_ingress: Mapping[str, Any],
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist edges, build chain, pin ``lineage_chain_digest`` on artifact."""
    artifact_id = str(artifact_body["artifact_id"])
    max_hops = effective_max_lineage_hops_v1(envelope)
    edge_kinds = persist_synthesis_artifact_lineage_edges_v1(
        session,
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        retrieval_ingress=retrieval_ingress,
        retrieval_subqueries=retrieval_subqueries,
    )
    chain = build_synthesis_artifact_lineage_chain_v1(
        session,
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        max_hops=max_hops,
        envelope=envelope,
    )
    truncated = detect_lineage_chain_truncated_v1(chain, max_hops=max_hops)
    pins = envelope.get("replay_pins") if isinstance(envelope, Mapping) else {}
    pin_match, _ = validate_lineage_chain_replay_pin_v1(
        pins if isinstance(pins, Mapping) else {},
        chain,
    )
    coverage = compute_lineage_coverage_v1(
        chain,
        truncated=truncated,
        pin_match=pin_match,
        edge_omissions=0,
    )
    digest = str(chain.get("lineage_chain_digest") or "")
    artifact_body["lineage_chain_digest"] = digest
    gap_rows = list_synthesis_lineage_gap_sd_rows_v1(
        truncated=truncated,
        pin_mismatch=not pin_match,
    )
    return {
        "lineage_chain_digest": digest,
        "lineage_coverage": coverage,
        "lineage_truncated": truncated,
        "lineage_edge_count": len(chain.get("edges") or []),
        "lineage_node_count": len(chain.get("nodes") or []),
        "persisted_edge_kinds": edge_kinds,
        "lineage_gap_sd_rows": gap_rows,
        "max_lineage_hops": max_hops,
    }


def enforce_synthesis_lineage_digest_law_v1(
    artifact_body: Mapping[str, Any],
    *,
    chain: Mapping[str, Any],
) -> None:
    expected = str(chain.get("lineage_chain_digest") or "")
    actual = str(artifact_body.get("lineage_chain_digest") or "")
    if expected and actual and expected != actual:
        raise SynthesisLineageError(
            "lineage_chain_digest_mismatch",
            detail={"expected": expected, "actual": actual},
        )


def build_synthesis_lineage_panel_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_body: Mapping[str, Any],
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Admin lineage panel — rebuild chain from persisted graph edges."""
    artifact_id = str(artifact_body.get("artifact_id") or "")
    max_hops = effective_max_lineage_hops_v1(envelope)
    chain = build_synthesis_artifact_lineage_chain_v1(
        session,
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        max_hops=max_hops,
        envelope=envelope,
    )
    truncated = detect_lineage_chain_truncated_v1(chain, max_hops=max_hops)
    digest = str(artifact_body.get("lineage_chain_digest") or "")
    chain_digest = str(chain.get("lineage_chain_digest") or "")
    pin_ok = not digest or not chain_digest or digest == chain_digest
    return {
        "surface_kind": "synthesis_lineage_panel",
        "phase08_synthesis_lineage_runtime_schema_version": (
            PHASE08_SYNTHESIS_LINEAGE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_LIN01_GATE_ID_V1,
        "artifact_id": artifact_id,
        "lineage_chain_digest": digest,
        "rebuilt_lineage_chain_digest": chain_digest,
        "lineage_digest_pin_match": pin_ok,
        "lineage_coverage": compute_lineage_coverage_v1(
            chain,
            truncated=truncated,
            pin_match=pin_ok,
            edge_omissions=0,
        ),
        "lineage_truncated": truncated,
        "max_lineage_hops": max_hops,
        "terminal": chain.get("terminal"),
        "lineage_edge_count": len(chain.get("edges") or []),
        "lineage_node_count": len(chain.get("nodes") or []),
        "lineage_edges": list(chain.get("edges") or [])[:32],
    }


def build_synthesis_lineage_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_lineage_law_v1",
        "phase08_synthesis_lineage_runtime_schema_version": (
            PHASE08_SYNTHESIS_LINEAGE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_LIN01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_LINEAGE_SPEC_REF_V1,
        "terminal_artifact_kind": SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1,
        "edge_kinds": [
            SYNTHESIS_EDGE_DERIVED_FROM_V1,
            SYNTHESIS_EDGE_INDEXES_V1,
            SYNTHESIS_EDGE_USES_V1,
        ],
        "sd_lineage_gap": SD_LINEAGE_GAP_V1,
        "upstream_rd_lineage_gap": RETRIEVAL_RD_LINEAGE_GAP_V1,
        "rules": [
            {"id": "SYN-LIN-01", "text": "Terminal node synthesis_intelligence / artifact_id"},
            {"id": "RET-LINEAGE-01", "text": "Reuse build_artifact_lineage_chain_v1"},
        ],
    }


def verify_gp08_lin01_synthesis_lineage_law_static() -> dict[str, Any]:
    errors: list[str] = []
    if SD_LINEAGE_GAP_V1 not in {"SD-LINEAGE-GAP"}:
        errors.append("sd_code_constant")
    if SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1 != "synthesis_intelligence":
        errors.append("terminal_kind")
    return {
        "id": GP08_LIN01_GATE_ID_V1,
        "name": "synthesis_artifact_lineage",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
