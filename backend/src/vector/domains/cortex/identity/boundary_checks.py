"""Phase 04 P04-02 — topology vs org-meaning boundary (pure validators).

Normative: `DOCS/cortex/04-identity/phase-04-topology-vs-meaning-doctrine.md`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.canonical.ontology import CanonicalStructuralEdgeKind
from vector.domains.cortex.continuity.edge_contracts import ContinuityEdgeKind

BOUNDARY_CHECKS_VERSION: Final[int] = 1

_FORBIDDEN_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "structural_edge_kind",
        "canonical_structural_edge_kind",
        "structural_arc",
        "materialization_dag_edge",
        "replay_dependency_edge",
        "transform_lineage_edge",
        "canonical_query_neighbor",
    }
)

_STRUCTURAL_EDGE_VALUES: Final[frozenset[str]] = frozenset(e.value for e in CanonicalStructuralEdgeKind)
_CONTINUITY_EDGE_VALUES: Final[frozenset[str]] = frozenset(e.value for e in ContinuityEdgeKind)


class TopologyMeaningBoundaryError(ValueError):
    """Raised when an org-meaning link payload smuggles Phase 03/3.5 topology."""


def validate_org_link_type_not_topology(link_type: str) -> None:
    """Reject Phase 03 / 3.5 edge discriminants when used as persisted `link_type` (**G-P04-08** alignment)."""
    if not isinstance(link_type, str) or not link_type.strip():
        msg = "link_type must be a non-empty string"
        raise TopologyMeaningBoundaryError(msg)
    _reject_link_type_value(link_type, field="link_type")


def _reject_link_type_value(value: object, *, field: str) -> None:
    if not isinstance(value, str):
        return
    if value in _STRUCTURAL_EDGE_VALUES:
        msg = f"{field} must not be a CanonicalStructuralEdgeKind value: {value!r}"
        raise TopologyMeaningBoundaryError(msg)
    if value in _CONTINUITY_EDGE_VALUES:
        msg = f"{field} must not be a ContinuityEdgeKind value: {value!r}"
        raise TopologyMeaningBoundaryError(msg)


def _reject_endpoint_dict(ep: Mapping[str, Any], *, role: str) -> None:
    for k in ("structural_edge_kind", "canonical_structural_edge_kind"):
        if k in ep:
            msg = f"{role} endpoint must not include topology key {k!r}"
            raise TopologyMeaningBoundaryError(msg)


def _is_embedded_continuity_contract_top_level(payload: Mapping[str, Any]) -> bool:
    """INV-P04-TOPO-05 — full ContinuityEdgeContract smuggled at top level."""
    return "continuity_edge_contract_version" in payload and "edge_kind" in payload


def validate_org_meaning_link_payload(payload: Mapping[str, Any]) -> None:
    """Validate a JSON-serializable org-meaning link draft (pre-DB).

    Raises:
        TopologyMeaningBoundaryError: if topology or Phase 3.5 continuity edge is smuggled as meaning.
    """
    forbidden = _FORBIDDEN_TOP_LEVEL_KEYS.intersection(payload.keys())
    if forbidden:
        msg = f"forbidden topology keys at top level: {sorted(forbidden)}"
        raise TopologyMeaningBoundaryError(msg)

    if _is_embedded_continuity_contract_top_level(payload):
        msg = "top-level ContinuityEdgeContract shape is forbidden on org meaning payloads"
        raise TopologyMeaningBoundaryError(msg)

    for field in ("link_type", "org_link_type"):
        if field in payload:
            _reject_link_type_value(payload[field], field=field)

    for role in ("source", "target"):
        ep = payload.get(role)
        if isinstance(ep, dict):
            _reject_endpoint_dict(ep, role=role)


def verify_topology_meaning_boundary_static() -> dict[str, Any]:
    """G-P04-08 / G-P04-TOPO-01 — self-check golden vectors (no DB)."""
    errors: list[str] = []
    # Negative cases — must raise
    negatives: list[tuple[str, Mapping[str, Any]]] = [
        ("structural_link_type", {"link_type": CanonicalStructuralEdgeKind.CONTAINED_IN.value}),
        ("continuity_link_type", {"org_link_type": ContinuityEdgeKind.PR_LINKS_ISSUE.value}),
        ("forbidden_key", {"structural_edge_kind": "contained_in"}),
        ("endpoint_topology", {"source": {"structural_edge_kind": "x"}}),
        ("embedded_contract", {"continuity_edge_contract_version": 1, "edge_kind": "pr_links_issue"}),
    ]
    for name, bad in negatives:
        try:
            validate_org_meaning_link_payload(bad)
        except TopologyMeaningBoundaryError:
            continue
        errors.append(f"expected rejection for case {name}")

    # Positive — minimal stub (keys only; values inert for boundary)
    try:
        validate_org_meaning_link_payload(
            {
                "link_type": "org.persona_belongs_to_handle",
                "evidence_raw_record_ids": [1, 2],
            }
        )
    except TopologyMeaningBoundaryError as exc:
        errors.append(f"unexpected rejection on minimal good payload: {exc}")

    passed = len(errors) == 0
    return {
        "id": "G-P04-08",
        "name": "topology_not_in_org_meaning_payload",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"boundary_checks_version": BOUNDARY_CHECKS_VERSION, "errors": errors},
    }
