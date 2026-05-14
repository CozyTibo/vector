"""Phase 05 P05-04 — graph import boundary (OrgGraphProjectionV1 ingress for OCTS).

Normative: ``DOCS/cortex/05-traversal/phase-05-graph-import-boundary-doctrine.md``.
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.identity.boundary_checks import (
    TopologyMeaningBoundaryError,
    validate_org_link_type_not_topology,
)
from vector.domains.cortex.identity.projection_export import (
    ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
    ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
    org_graph_projection_canonical_json_bytes,
    org_graph_projection_stable_hash_sha256,
    validate_org_graph_projection_v1_shape,
    verify_org_graph_export_forbidden_leakage,
)

GIB_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# Walk / ingress JSON scan — extends P04 **G-P04-10** token class (**G-P05-IMPORT-02**).
_EXTRA_TRAVERSAL_INGRESS_SUBSTRINGS_LOWER: Final[tuple[str, ...]] = ("canonical_transform_node",)


class GraphImportBoundaryError(ValueError):
    """Raised when an import bundle is not admissible for OCTS traversal."""


def list_oct_traversal_ingress_token_violations(projection: dict[str, Any]) -> list[str]:
    """**G-P05-IMPORT-02** — forbidden Phase-03 / ingress tokens on canonical projection JSON."""
    errors = list(verify_org_graph_export_forbidden_leakage(projection))
    raw = org_graph_projection_canonical_json_bytes(projection).decode("utf-8").lower()
    for token in _EXTRA_TRAVERSAL_INGRESS_SUBSTRINGS_LOWER:
        if token in raw:
            errors.append(f"forbidden_ingress_token:{token}")
    return errors


def list_oct_graph_import_violations(projection: dict[str, Any]) -> list[str]:
    """Structural P04 shape + **G-P05-IMPORT-01** authority + topology link_type + token scan."""
    errors: list[str] = []
    errors.extend(validate_org_graph_projection_v1_shape(projection))
    errors.extend(list_oct_traversal_ingress_token_violations(projection))

    edges = projection.get("edges")
    if isinstance(edges, list):
        for i, raw in enumerate(edges):
            if not isinstance(raw, dict):
                continue
            e = raw
            auth = e.get("link_authority")
            if auth != "authoritative":
                eid = e.get("id", i)
                errors.append(f"edge_not_authoritative_traversable:{eid!r}:{auth!r}")
            lt = e.get("link_type")
            if isinstance(lt, str):
                try:
                    validate_org_link_type_not_topology(lt)
                except TopologyMeaningBoundaryError as exc:
                    eid = e.get("id", i)
                    errors.append(f"edge_topology_link_type:{eid!r}:{exc}")
    return errors


def validate_oct_traversal_import_projection(projection: dict[str, Any]) -> None:
    """Reject import bundles that violate **GIB** / **FS-GIB-02**."""
    v = list_oct_graph_import_violations(projection)
    if v:
        msg = "graph import boundary violations: " + "; ".join(v[:20])
        if len(v) > 20:
            msg += f"; …(+{len(v) - 20} more)"
        raise GraphImportBoundaryError(msg)


def validate_inner_projection_matches_stable_hash(
    inner: dict[str, Any], *, expected_stable_hash_sha256: str
) -> None:
    """**RULE GIB-01** — inner projection bytes must match declared stable hash."""
    actual = org_graph_projection_stable_hash_sha256(inner)
    if actual != expected_stable_hash_sha256:
        msg = (
            "projection_content_hash mismatch: "
            f"expected {expected_stable_hash_sha256!r}, recomputed {actual!r}"
        )
        raise GraphImportBoundaryError(msg)


def validate_temporal_anchor_has_projection_content_hash(anchor: Mapping[str, Any]) -> None:
    """**FS-GIB-03** — walk execution requires pinned projection identity in anchor."""
    h = anchor.get("projection_content_hash")
    if not isinstance(h, str) or not h.strip():
        msg = "FS-GIB-03: temporal_anchor.projection_content_hash must be a non-empty string"
        raise GraphImportBoundaryError(msg)


def _minimal_inner_projection_one_edge(*, link_authority: str) -> dict[str, Any]:
    eid = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    return {
        "projection_schema_version": ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
        "tenant_id": str(uuid.UUID(int=0)),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": str(uuid.UUID(int=1)),
                "entity_kind": "human_actor",
                "identity_key_fingerprint": "fp",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            }
        ],
        "edges": [
            {
                "kind": "org_meaning_link",
                "id": eid,
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(uuid.UUID(int=1)),
                "target_entity_id": str(uuid.UUID(int=1)),
                "link_class": "authoritative",
                "link_authority": link_authority,
                "confidence_class": "declared",
                "evidence_raw_record_ids": [1, 2],
                "rule_id": None,
                "valid_from": None,
                "valid_to": None,
                "revoked_at": None,
                "supersedes_link_id": None,
                "promoted_from_candidate_id": None,
                "promotion_policy_id": None,
                "link_row_stable_id": eid,
            }
        ],
    }


def verify_gp05_import01_traversable_subset_authoritative_static() -> dict[str, Any]:
    """**G-P05-IMPORT-01** — traversable edges ⊆ authoritative export (shape + authority)."""
    errors: list[str] = []
    good = _minimal_inner_projection_one_edge(link_authority="authoritative")
    bad_hint = _minimal_inner_projection_one_edge(link_authority="hint")
    bad_candidate = _minimal_inner_projection_one_edge(link_authority="candidate")

    errors.extend(list_oct_graph_import_violations(good))
    if list_oct_graph_import_violations(bad_hint) == []:
        errors.append("expected_hint_link_authority_rejected")
    if list_oct_graph_import_violations(bad_candidate) == []:
        errors.append("expected_candidate_link_authority_rejected")

    topo_edge = copy.deepcopy(good)
    assert isinstance(topo_edge["edges"], list)
    edge0 = topo_edge["edges"][0]
    assert isinstance(edge0, dict)
    edge0["link_type"] = "membership"  # CanonicalStructuralEdgeKind value
    if list_oct_graph_import_violations(topo_edge) == []:
        errors.append("expected_topology_link_type_rejected")

    passed = len(errors) == 0
    return {
        "id": "G-P05-IMPORT-01",
        "name": "traversable_edges_authoritative_export_only",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"gib_runtime_schema_version": GIB_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_import02_forbidden_ingress_tokens_static() -> dict[str, Any]:
    """**G-P05-IMPORT-02** — extends P04 forbidden topology scan + ingress tokens."""
    errors: list[str] = []
    good = _minimal_inner_projection_one_edge(link_authority="authoritative")
    errors.extend(list_oct_graph_import_violations(good))

    poisoned = copy.deepcopy(good)
    n0 = poisoned["nodes"][0]
    assert isinstance(n0, dict)
    n0["entity_kind"] = "x canonical_transform_node y"
    if list_oct_graph_import_violations(poisoned) == []:
        errors.append("expected_canonical_transform_node_token_rejected")

    passed = len(errors) == 0
    return {
        "id": "G-P05-IMPORT-02",
        "name": "forbidden_phase03_tokens_in_ingress",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"gib_runtime_schema_version": GIB_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }
