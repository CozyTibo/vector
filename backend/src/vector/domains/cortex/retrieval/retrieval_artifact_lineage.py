"""Phase 07 P07-21 — artifact lineage retrieval (terminal→root explorer).

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md`` §Lineage.
**RET-LINEAGE-01** terminal→root chain with ``max_lineage_hops`` cap; **RET-LINEAGE-02** chain
digest pinned in replay pins; incomplete/truncated chains emit ``RD-LINEAGE-GAP``.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.lineage_chain_builder import build_artifact_lineage_chain_v1
from vector.domains.cortex.lineage.lineage_explainability_projection import (
    build_lineage_explainability_v1,
)
from vector.domains.cortex.lineage.lineage_receipt_projection import lineage_receipt_digest_v1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    RETRIEVAL_OMISSION_SEMANTICS_BY_RD_V1,
    RETRIEVAL_RD_CODES_REGISTRY_V1,
)
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import format_retrieval_lookup_id_v1

PHASE07_RETRIEVAL_ARTIFACT_LINEAGE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_LINEAGE01_GATE_ID_V1: Final[str] = "G-P07-LINEAGE-01"

RETRIEVAL_ARTIFACT_LINEAGE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md"
)

RET_LINEAGE01_RULE_ID_V1: Final[str] = "RET-LINEAGE-01"

RET_LINEAGE02_RULE_ID_V1: Final[str] = "RET-LINEAGE-02"

RETRIEVAL_RD_LINEAGE_GAP_V1: Final[str] = "RD-LINEAGE-GAP"

_LINEAGE_SCOPED_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {"lineage_explorer", "traversal_lineage"}
)

_RETRIEVAL_LINEAGE_GAP_TOTAL_V1: int = 0

_RETRIEVAL_LINEAGE_TRUNCATED_TOTAL_V1: int = 0


class RetrievalArtifactLineageError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_retrieval_lineage_gap_total_v1() -> int:
    return _RETRIEVAL_LINEAGE_GAP_TOTAL_V1


def get_retrieval_lineage_truncated_total_v1() -> int:
    return _RETRIEVAL_LINEAGE_TRUNCATED_TOTAL_V1


def record_retrieval_lineage_gap_v1(*, reason: str) -> None:
    global _RETRIEVAL_LINEAGE_GAP_TOTAL_V1
    _RETRIEVAL_LINEAGE_GAP_TOTAL_V1 += 1


def record_retrieval_lineage_truncated_v1(*, hop_cap: int) -> None:
    global _RETRIEVAL_LINEAGE_TRUNCATED_TOTAL_V1
    _RETRIEVAL_LINEAGE_TRUNCATED_TOTAL_V1 += 1


def _node_key(kind: str, ref: str) -> str:
    return f"{kind}:{ref}"


def extract_lineage_terminal_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_lookup_id: str,
) -> tuple[str, str]:
    """Resolve terminal artifact kind/ref for lineage traversal."""
    addressing = envelope.get("addressing")
    if isinstance(addressing, dict):
        kind = addressing.get("artifact_kind")
        ref = addressing.get("artifact_ref") or addressing.get("retrieval_lineage_ref")
        if kind is not None and ref is not None and str(ref).strip():
            return str(kind).strip(), str(ref).strip()
    return "retrieval_index", str(retrieval_lookup_id).strip()


def compute_node_hop_depths_v1(chain: Mapping[str, Any]) -> dict[str, int]:
    """Hop depth from terminal (0) toward upstream roots."""
    terminal = chain.get("terminal")
    if not isinstance(terminal, dict):
        return {}
    tk = _node_key(str(terminal["kind"]), str(terminal["ref"]))
    depths: dict[str, int] = {tk: 0}
    parents_of: dict[str, list[str]] = defaultdict(list)
    for edge in chain.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        parents_of[str(edge.get("to", ""))].append(str(edge.get("from", "")))
    frontier = [tk]
    hop = 0
    while frontier:
        hop += 1
        next_frontier: list[str] = []
        for node in frontier:
            for parent in parents_of.get(node, []):
                if parent and parent not in depths:
                    depths[parent] = hop
                    next_frontier.append(parent)
        frontier = next_frontier
    return depths


def detect_lineage_chain_truncated_v1(
    chain: Mapping[str, Any],
    *,
    max_hops: int,
) -> bool:
    """True when hop cap may have cut traversal before upstream closure."""
    depths = compute_node_hop_depths_v1(chain)
    if not depths:
        return False
    if max(depths.values()) >= max(1, max_hops):
        return True
    edges = chain.get("edges") or []
    if not edges:
        return False
    terminal = chain.get("terminal")
    if not isinstance(terminal, dict):
        return False
    tk = _node_key(str(terminal["kind"]), str(terminal["ref"]))
    parents_of: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if isinstance(edge, dict):
            parents_of[str(edge.get("to", ""))].append(str(edge.get("from", "")))
    leaves = [k for k in depths if k != tk and k not in parents_of]
    for leaf in leaves:
        if depths.get(leaf, 0) >= max(1, max_hops):
            return True
    return False


def compute_lineage_coverage_v1(
    chain: Mapping[str, Any],
    *,
    truncated: bool,
    pin_match: bool,
    edge_omissions: int,
) -> str:
    if truncated or not pin_match or edge_omissions > 0:
        return "gap" if truncated or not pin_match else "partial"
    nodes = chain.get("nodes") or []
    edges = chain.get("edges") or []
    if not nodes:
        return "gap"
    if edges and edge_omissions == 0 and not truncated:
        return "complete"
    return "partial" if nodes else "gap"


def validate_lineage_chain_replay_pin_v1(
    replay_pins: Mapping[str, Any],
    chain: Mapping[str, Any],
) -> tuple[bool, str | None]:
    """**RET-LINEAGE-02** — pinned ``lineage_chain_digest`` must match built chain."""
    expected = replay_pins.get("lineage_chain_digest")
    if expected is None or not str(expected).strip():
        return True, None
    actual = str(chain.get("lineage_chain_digest") or "")
    exp = str(expected).strip()
    if actual == exp:
        return True, None
    return False, f"expected={exp} actual={actual}"


def list_lineage_gap_omissions_v1(
    *,
    upstream_trigger: str,
    truncated: bool = False,
    pin_mismatch: bool = False,
    edge_omission_count: int = 0,
) -> list[dict[str, Any]]:
    if not (truncated or pin_mismatch or edge_omission_count > 0):
        return []
    record_retrieval_lineage_gap_v1(reason=upstream_trigger)
    trigger = upstream_trigger
    if pin_mismatch:
        trigger = "lineage_chain_digest_mismatch"
    elif truncated:
        trigger = "max_lineage_hops_truncated"
    elif edge_omission_count > 0:
        trigger = "lineage_edge_omission"
    return [
        {
            "retrieval_omission_class": RETRIEVAL_RD_LINEAGE_GAP_V1,
            "omission_semantics": RETRIEVAL_OMISSION_SEMANTICS_BY_RD_V1.get(
                RETRIEVAL_RD_LINEAGE_GAP_V1, "omitted_upstream_gap"
            ),
            "upstream_trigger": trigger,
            "gate_id": GP07_LINEAGE01_GATE_ID_V1,
        }
    ]


def build_retrieval_lineage_chain_for_query_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    terminal_artifact_kind: str,
    terminal_artifact_ref: str,
    max_hops: int,
) -> dict[str, Any]:
    cap = max(1, min(int(max_hops), 256))
    return build_artifact_lineage_chain_v1(
        session,
        tenant_id=tenant_id,
        terminal_artifact_kind=terminal_artifact_kind,
        terminal_artifact_ref=terminal_artifact_ref,
        max_hops=cap,
    )


def expand_lineage_chain_to_hits_v1(
    chain: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID | str,
    retrieval_lookup_id: str,
    row: Any,
    workload_class: str,
    execution_partition: str,
    replay_posture: str = "stable",
    lineage_coverage: str,
) -> list[dict[str, Any]]:
    """Map lineage nodes to retrieval evidence hits for ``lineage_explorer``."""
    depths = compute_node_hop_depths_v1(chain)
    terminal = chain.get("terminal")
    if not isinstance(terminal, dict):
        return []
    nodes = chain.get("nodes") or []
    hits: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("artifact_kind", ""))
        ref = str(node.get("artifact_ref", ""))
        nk = _node_key(kind, ref)
        hop = int(depths.get(nk, 0))
        if nk == _node_key(str(terminal["kind"]), str(terminal["ref"])):
            lid = format_retrieval_lookup_id_v1(retrieval_lookup_id)
        else:
            lid = format_retrieval_lookup_id_v1(
                hash_reasoning_canonical_json_sha256_v1(
                    {"lineage_node": nk, "terminal_lookup_id": retrieval_lookup_id}
                )
            )
        hits.append(
            {
                "retrieval_lookup_id": lid,
                "artifact_kind": kind,
                "artifact_ref": ref,
                "lineage_hop_count": hop,
                "lineage_coverage": lineage_coverage,
                "evidence_legality_class": str(
                    getattr(row, "causal_legality_class", "verified") or "verified"
                ),
                "provenance": {
                    "tenant_id": str(tenant_id),
                    "replay_posture": replay_posture,
                    "evidence_legality_class": "derived",
                    "lineage_coverage": lineage_coverage,
                    "artifact_kind": kind,
                    "provenance_class": "lineage_node",
                    "lineage_chain_digest": chain.get("lineage_chain_digest"),
                },
                "workload_class": workload_class,
                "execution_partition": execution_partition,
            }
        )
    hits.sort(key=lambda h: (int(h.get("lineage_hop_count", 0)), str(h.get("artifact_ref", ""))))
    return hits


def apply_lineage_coverage_to_hits_v1(
    hits: Sequence[Mapping[str, Any]],
    *,
    lineage_coverage: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for hit in hits:
        row_hit = dict(hit)
        prov = row_hit.get("provenance")
        if isinstance(prov, dict):
            prov = dict(prov)
            prov["lineage_coverage"] = lineage_coverage
            row_hit["provenance"] = prov
        row_hit["lineage_coverage"] = lineage_coverage
        out.append(row_hit)
    return out


def apply_retrieval_lineage_binding_to_query_v1(
    *,
    session: Session,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    workload_class: str,
    execution_partition: str,
    hits: list[dict[str, Any]],
    omissions: list[dict[str, Any]],
    replay_pins: Mapping[str, Any],
    retrieval_lookup_id: str,
    row: Any,
    caps: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind lineage chain; expand hits for ``lineage_explorer``; emit ``RD-LINEAGE-GAP``."""
    wl = str(workload_class)
    terminal_kind, terminal_ref = extract_lineage_terminal_v1(
        envelope=envelope,
        retrieval_lookup_id=retrieval_lookup_id,
    )
    max_hops = int(caps.get("max_lineage_hops", 64) or 64)
    chain = build_retrieval_lineage_chain_for_query_v1(
        session,
        tenant_id=tenant_id,
        terminal_artifact_kind=terminal_kind,
        terminal_artifact_ref=terminal_ref,
        max_hops=max_hops,
    )
    truncated = detect_lineage_chain_truncated_v1(chain, max_hops=max_hops)
    if truncated:
        record_retrieval_lineage_truncated_v1(hop_cap=max_hops)
    pin_ok, pin_detail = validate_lineage_chain_replay_pin_v1(replay_pins, chain)
    edge_omissions = sum(
        1
        for e in chain.get("edges") or []
        if isinstance(e, dict) and (e.get("omission_summary") or {})
    )
    coverage = compute_lineage_coverage_v1(
        chain,
        truncated=truncated,
        pin_match=pin_ok,
        edge_omissions=edge_omissions,
    )
    out_omissions = list(omissions)
    out_omissions.extend(
        list_lineage_gap_omissions_v1(
            upstream_trigger="lineage_explorer",
            truncated=truncated,
            pin_mismatch=not pin_ok,
            edge_omission_count=edge_omissions,
        )
    )
    explain = build_lineage_explainability_v1(chain)
    binding_envelope: dict[str, Any] = {
        "schema_version": PHASE07_RETRIEVAL_ARTIFACT_LINEAGE_RUNTIME_SCHEMA_VERSION,
        "bind_state": "bound",
        "terminal_artifact_kind": terminal_kind,
        "terminal_artifact_ref": terminal_ref,
        "lineage_chain_digest": chain.get("lineage_chain_digest"),
        "lineage_coverage": coverage,
        "max_lineage_hops": max_hops,
        "truncated": truncated,
        "lineage_chain_digest_pin_match": pin_ok,
        "lineage_chain_digest_pin_detail": pin_detail,
        "node_count": len(chain.get("nodes") or []),
        "edge_count": len(chain.get("edges") or []),
    }
    out_hits = list(hits)
    if wl == "lineage_explorer":
        out_hits = expand_lineage_chain_to_hits_v1(
            chain,
            tenant_id=tenant_id,
            retrieval_lookup_id=retrieval_lookup_id,
            row=row,
            workload_class=wl,
            execution_partition=execution_partition,
            lineage_coverage=coverage,
        )
    elif wl in _LINEAGE_SCOPED_WORKLOADS_V1 or out_hits:
        out_hits = apply_lineage_coverage_to_hits_v1(out_hits, lineage_coverage=coverage)
        max_nodes = int(caps.get("max_hits", 64) or 64)
        if len(out_hits) > max_nodes and wl != "lineage_explorer":
            out_hits = out_hits[:max_nodes]
    return {
        "hits": out_hits,
        "omissions": out_omissions,
        "lineage_binding_envelope": binding_envelope,
        "lineage_chain": chain,
        "lineage_explainability": explain,
    }


def build_retrieval_lineage_explorer_chain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_kind: str,
    artifact_ref: str,
    max_hops: int = 64,
) -> dict[str, Any]:
    """Admin terminal→root explorer payload."""
    chain = build_retrieval_lineage_chain_for_query_v1(
        session,
        tenant_id=tenant_id,
        terminal_artifact_kind=artifact_kind,
        terminal_artifact_ref=artifact_ref,
        max_hops=max_hops,
    )
    truncated = detect_lineage_chain_truncated_v1(chain, max_hops=max_hops)
    return {
        "chain": chain,
        "explainability": build_lineage_explainability_v1(chain),
        "lineage_coverage": compute_lineage_coverage_v1(
            chain,
            truncated=truncated,
            pin_match=True,
            edge_omissions=sum(
                1
                for e in chain.get("edges") or []
                if isinstance(e, dict) and (e.get("omission_summary") or {})
            ),
        ),
        "truncated": truncated,
        "max_lineage_hops": max(1, min(int(max_hops), 256)),
    }


def build_retrieval_lineage_explorer_catalog_v1() -> dict[str, Any]:
    """Admin lineage explorer catalog."""
    return {
        "retrieval_artifact_lineage_runtime_schema_version": (
            PHASE07_RETRIEVAL_ARTIFACT_LINEAGE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_LINEAGE01_GATE_ID_V1,
        "spec_ref": RETRIEVAL_ARTIFACT_LINEAGE_SPEC_REF_V1,
        "rules": [
            {
                "id": RET_LINEAGE01_RULE_ID_V1,
                "text": "Terminal→root lineage chain with max_lineage_hops cap",
            },
            {
                "id": RET_LINEAGE02_RULE_ID_V1,
                "text": "lineage_chain_digest pinned in replay_pins for replay-safe workloads",
            },
        ],
        "lineage_scoped_workloads": sorted(_LINEAGE_SCOPED_WORKLOADS_V1),
        "rd_lineage_gap_code": RETRIEVAL_RD_LINEAGE_GAP_V1,
        "observability": {
            "lineage_gap_metric": "retrieval_lineage_gap_total",
            "lineage_truncated_metric": "retrieval_lineage_truncated_total",
            "lineage_coverage_field": "lineage_coverage",
        },
        "golden_case_id": "query/lineage_explorer_minimal_v1",
    }


def _golden_vectors_v1_root() -> Any:
    from pathlib import Path

    here = Path(__file__).resolve()
    tail = (
        "tests",
        "vector",
        "domains",
        "cortex",
        "retrieval",
        "retrieval_golden_vectors",
        "v1",
    )
    for root in [here, *here.parents]:
        candidate = root.joinpath(*tail)
        if candidate.is_dir():
            return candidate
        alt = root / "backend" / Path(*tail)
        if alt.is_dir():
            return alt
    raise FileNotFoundError("retrieval_golden_vectors/v1 not found")


def load_retrieval_lineage_golden_case_v1(case_id: str) -> dict[str, Any]:
    path = _golden_vectors_v1_root() / "cases" / case_id / "case.json"
    if not path.is_file():
        raise FileNotFoundError(f"golden case not found: {case_id}")
    loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RetrievalArtifactLineageError("golden_case_not_object")
    return loaded


def run_retrieval_golden_lineage_explorer_case_v1(case: Mapping[str, Any]) -> dict[str, Any]:
    """Static golden harness for ``query/lineage_explorer_minimal_v1``."""
    inputs = case.get("inputs")
    expected = case.get("expected")
    if not isinstance(inputs, dict) or not isinstance(expected, dict):
        raise RetrievalArtifactLineageError("golden_case_missing_inputs_or_expected")
    terminal = inputs.get("terminal")
    if not isinstance(terminal, dict):
        raise RetrievalArtifactLineageError("golden_terminal_required")
    fixture = inputs.get("chain_fixture")
    if not isinstance(fixture, dict):
        raise RetrievalArtifactLineageError("golden_chain_fixture_required")
    max_hops = int(inputs.get("max_lineage_hops", 32) or 32)
    body = {
        "tenant_id": str(inputs.get("tenant_id", "00000000-0000-0000-0000-000000000000")),
        "terminal": terminal,
        "nodes": list(fixture.get("nodes") or []),
        "edges": list(fixture.get("edges") or []),
    }
    body["lineage_chain_digest"] = lineage_receipt_digest_v1(body)
    pins = inputs.get("replay_pins")
    if not isinstance(pins, dict):
        pins = {}
    pin_ok, _ = validate_lineage_chain_replay_pin_v1(pins, body)
    truncated = detect_lineage_chain_truncated_v1(body, max_hops=max_hops)
    edge_om = sum(
        1 for e in body.get("edges") or [] if isinstance(e, dict) and (e.get("omission_summary") or {})
    )
    coverage = compute_lineage_coverage_v1(
        body, truncated=truncated, pin_match=pin_ok, edge_omissions=edge_om
    )
    gaps = list_lineage_gap_omissions_v1(
        upstream_trigger="golden",
        truncated=truncated,
        pin_mismatch=not pin_ok,
        edge_omission_count=edge_om,
    )
    passed = (
        len(body.get("nodes") or []) == int(expected.get("node_count", 0))
        and coverage == str(expected.get("lineage_coverage", ""))
        and bool(expected.get("gp07_lineage01_passed", False))
        and (not expected.get("expects_rd_lineage_gap") or bool(gaps))
    )
    if not passed:
        raise RetrievalArtifactLineageError(
            "golden_lineage_expectation_failed",
            detail={
                "node_count": len(body.get("nodes") or []),
                "coverage": coverage,
                "truncated": truncated,
                "pin_ok": pin_ok,
                "gaps": gaps,
            },
        )
    return {
        "case_id": case.get("case_id"),
        "gate_id": case.get("gate_id"),
        "gp07_lineage01_passed": True,
        "lineage_coverage": coverage,
        "lineage_chain_digest": body.get("lineage_chain_digest"),
    }


def _lineage_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_LINEAGE01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_lineage01_terminal_to_root_cap_static() -> dict[str, Any]:
    """**G-P07-LINEAGE-01** — hop cap, RD-LINEAGE-GAP registry, catalog law."""
    errors: list[str] = []
    if RETRIEVAL_RD_LINEAGE_GAP_V1 not in RETRIEVAL_RD_CODES_REGISTRY_V1:
        errors.append("rd_lineage_gap_not_in_registry")
    fixture = {
        "tenant_id": "00000000-0000-0000-0000-000000000000",
        "terminal": {"kind": "retrieval_index", "ref": "sha256:terminal"},
        "nodes": [
            {"artifact_kind": "retrieval_index", "artifact_ref": "sha256:terminal"},
            {"artifact_kind": "tcre_chain", "artifact_ref": "chain-1"},
        ],
        "edges": [
            {
                "lineage_edge_id": "e1",
                "from": "tcre_chain:chain-1",
                "to": "retrieval_index:sha256:terminal",
                "edge_kind": "binds",
                "omission_summary": {},
                "degradation_propagation": {},
                "replay_identity": "r1",
            }
        ],
    }
    fixture["lineage_chain_digest"] = lineage_receipt_digest_v1(fixture)
    depths = compute_node_hop_depths_v1(fixture)
    if depths.get("retrieval_index:sha256:terminal") != 0:
        errors.append("terminal_hop_zero")
    if depths.get("tcre_chain:chain-1") != 1:
        errors.append("upstream_hop_one")
    truncated = detect_lineage_chain_truncated_v1(fixture, max_hops=1)
    if not truncated:
        errors.append("truncation_at_cap")
    gaps = list_lineage_gap_omissions_v1(upstream_trigger="static", truncated=True)
    if not gaps or gaps[0].get("retrieval_omission_class") != RETRIEVAL_RD_LINEAGE_GAP_V1:
        errors.append("rd_lineage_gap_emission")
    pin_ok, _ = validate_lineage_chain_replay_pin_v1(
        {"lineage_chain_digest": fixture["lineage_chain_digest"]},
        fixture,
    )
    if not pin_ok:
        errors.append("pin_match_expected")
    bad_pin, _ = validate_lineage_chain_replay_pin_v1(
        {"lineage_chain_digest": "sha256:wrong"},
        fixture,
    )
    if bad_pin:
        errors.append("pin_mismatch_expected")
    cat = build_retrieval_lineage_explorer_catalog_v1()
    if cat["gate_id"] != GP07_LINEAGE01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    if "lineage_explorer" not in cat["lineage_scoped_workloads"]:
        errors.append("lineage_explorer_workload")
    return _lineage_meta("gp07_lineage01_terminal_to_root_cap", errors)


def verify_gp07_lineage01_golden_corpus_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        case = load_retrieval_lineage_golden_case_v1("query/lineage_explorer_minimal_v1")
        run_retrieval_golden_lineage_explorer_case_v1(case)
    except (FileNotFoundError, RetrievalArtifactLineageError) as exc:
        errors.append(f"golden_corpus:{exc}")
    return _lineage_meta("gp07_lineage01_golden_corpus", errors)
