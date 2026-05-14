"""Phase 05 P05-06 — directed multigraph model (neighbor order + edge fingerprints).

Normative: ``DOCS/cortex/05-traversal/phase-05-multigraph-model-doctrine.md``,
``DOCS/cortex/05-traversal/phase-05-normative-index.md`` (edge fingerprint law).

**RULE MG-01** — neighbor expansion: outgoing edges sorted by ``edge_fingerprint`` ascending.
**RULE MG-02** — diagnostic multiset: lexicographically sorted ``edge_fingerprint`` list.
**FS-MG-01** — duplicate ``edge_fingerprint`` for distinct org links (illegal).
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, cast

from vector.domains.cortex.identity.projection_export import validate_org_graph_projection_v1_shape
from vector.domains.cortex.traversal.graph_import_boundary import list_oct_graph_import_violations

MG_RUNTIME_SCHEMA_VERSION: Final[int] = 1

_EDGE_FINGERPRINT_PREFIX: Final[str] = "sha256:"


class MultigraphModelError(ValueError):
    """Raised when multigraph / fingerprint invariants are violated."""


def _repo_root_with_octs_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "05-traversal" / "phase-05-normative-index.md"
        if marker.is_file():
            return root
    msg = (
        "Could not locate DOCS/cortex/05-traversal/phase-05-normative-index.md "
        "from multigraph_model."
    )
    raise RuntimeError(msg)


def octs_multigraph_neighbor_order_fixture_dir() -> Path:
    """Directory holding **G-P05-MG-01** golden inner projection + expected expansion."""
    root = _repo_root_with_octs_docs()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "multigraph"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"multigraph golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def _nfc_strings(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {str(k): _nfc_strings(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_nfc_strings(x) for x in obj]
    return obj


def edge_fingerprint_key_object_v1(edge: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical key object for **INVARIANT EFP-01** (sorted JSON → SHA-256).

    Key parts exactly:
    ``bundle_scope_id``, ``link_row_stable_id``, ``link_type_code``,
    ``source_node_id``, ``target_node_id``, ``validity_half_open``.
    """
    for k in ("link_row_stable_id", "link_type", "source_entity_id", "target_entity_id"):
        if k not in edge:
            msg = f"edge missing required field for fingerprint: {k!r}"
            raise MultigraphModelError(msg)
    bundle = edge.get("bundle_scope_id", None)
    validity = _nfc_strings(
        {
            "valid_from": edge.get("valid_from"),
            "valid_to": edge.get("valid_to"),
        }
    )
    key = _nfc_strings(
        {
            "bundle_scope_id": bundle,
            "link_row_stable_id": str(edge["link_row_stable_id"]),
            "link_type_code": str(edge["link_type"]),
            "source_node_id": str(edge["source_entity_id"]),
            "target_node_id": str(edge["target_entity_id"]),
            "validity_half_open": validity,
        }
    )
    if not isinstance(key, dict):
        msg = "internal_error: edge fingerprint key must be a JSON object"
        raise MultigraphModelError(msg)
    return cast(dict[str, Any], key)


def edge_fingerprint_canonical_json_bytes_v1(edge: Mapping[str, Any]) -> bytes:
    key_obj = edge_fingerprint_key_object_v1(edge)
    return json.dumps(key_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_edge_fingerprint_v1(edge: Mapping[str, Any]) -> str:
    """Return ``sha256:`` + 64 hex lowercase (**§8 serialization**)."""
    digest = hashlib.sha256(edge_fingerprint_canonical_json_bytes_v1(edge)).hexdigest()
    return f"{_EDGE_FINGERPRINT_PREFIX}{digest}"


def _parse_iso_to_unix_ns(value: Any) -> int | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1_000_000_000)


def edge_eligible_at_t_as_of_unix_ns(edge: Mapping[str, Any], t_as_of_unix_ns: int) -> bool:
    """Half-open validity filter (**multigraph §6**) before neighbor ordering."""
    vf_ns = _parse_iso_to_unix_ns(edge.get("valid_from"))
    vt_ns = _parse_iso_to_unix_ns(edge.get("valid_to"))
    if vf_ns is not None and t_as_of_unix_ns < vf_ns:
        return False
    if vt_ns is not None and t_as_of_unix_ns >= vt_ns:
        return False
    return True


def _is_traversable_org_meaning_link(edge: Mapping[str, Any]) -> bool:
    return edge.get("kind") == "org_meaning_link" and edge.get("link_authority") == "authoritative"


def list_outgoing_traversable_edges_v1(
    edges: Sequence[Mapping[str, Any]],
    *,
    source_node_id: str,
    t_as_of_unix_ns: int | None,
) -> list[Mapping[str, Any]]:
    out: list[Mapping[str, Any]] = []
    for e in edges:
        if not isinstance(e, dict):
            continue
        if not _is_traversable_org_meaning_link(e):
            continue
        if str(e.get("source_entity_id")) != source_node_id:
            continue
        if t_as_of_unix_ns is not None and not edge_eligible_at_t_as_of_unix_ns(e, t_as_of_unix_ns):
            continue
        out.append(e)
    return out


def neighbor_expansion_fingerprints_ordered_v1(
    edges: Sequence[Mapping[str, Any]],
    *,
    source_node_id: str,
    t_as_of_unix_ns: int | None = None,
) -> list[str]:
    """**RULE MG-01** — deterministic neighbor list for ``source_node_id``."""
    outgoing = list_outgoing_traversable_edges_v1(
        edges, source_node_id=source_node_id, t_as_of_unix_ns=t_as_of_unix_ns
    )
    fps = [compute_edge_fingerprint_v1(e) for e in outgoing]
    return sorted(fps)


def canonical_diagnostic_multiset_fingerprints_v1(
    fingerprints: Sequence[str],
) -> list[str]:
    """**RULE MG-02** — sorted multiset for unordered diagnostic views."""
    return sorted(fingerprints)


def list_fs_mg01_duplicate_fingerprint_violations(
    edges: Sequence[Mapping[str, Any]],
) -> list[str]:
    """**FS-MG-01** — same ``edge_fingerprint`` for two distinct org links (by ``id``)."""
    fp_to_link_ids: dict[str, list[str]] = {}
    for e in edges:
        if not isinstance(e, dict):
            continue
        if not _is_traversable_org_meaning_link(e):
            continue
        eid = e.get("id")
        if not isinstance(eid, str):
            continue
        fp = compute_edge_fingerprint_v1(e)
        fp_to_link_ids.setdefault(fp, []).append(eid)
    errors: list[str] = []
    for fp, ids in sorted(fp_to_link_ids.items(), key=lambda kv: kv[0]):
        uniq = sorted(set(ids))
        if len(uniq) > 1:
            errors.append(f"fs_mg01_duplicate_fingerprint:{fp}:links={uniq}")
    return errors


def neighbor_order_expected_bytes_v1(fingerprints: Sequence[str]) -> bytes:
    """Byte-stable encoding for **G-P05-MG-01** golden comparison."""
    return json.dumps(list(fingerprints), separators=(",", ":")).encode("utf-8")


def verify_gp05_mg01_neighbor_order_golden_static() -> dict[str, Any]:
    """**G-P05-MG-01** — golden parallel-edge graph yields stable neighbor expansion bytes."""
    errors: list[str] = []
    d = octs_multigraph_neighbor_order_fixture_dir()
    inner_path = d / "neighbor_order_inner_v1.json"
    expected_path = d / "neighbor_order_expected_v1.json"
    if not inner_path.is_file():
        errors.append(f"missing_fixture:{inner_path}")
    if not expected_path.is_file():
        errors.append(f"missing_fixture:{expected_path}")
    if errors:
        return {
            "id": "G-P05-MG-01",
            "name": "neighbor_order_golden_bytes",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"mg_runtime_schema_version": MG_RUNTIME_SCHEMA_VERSION, "errors": errors},
        }

    inner = json.loads(inner_path.read_text(encoding="utf-8"))
    if not isinstance(inner, dict):
        errors.append("inner_projection_not_object")
    else:
        errors.extend(validate_org_graph_projection_v1_shape(inner))
        errors.extend(list_oct_graph_import_violations(inner))
        edges = inner.get("edges")
        if isinstance(edges, list) and all(isinstance(x, dict) for x in edges):
            src = "11111111-1111-1111-1111-111111111111"
            ordered = neighbor_expansion_fingerprints_ordered_v1(
                edges, source_node_id=src, t_as_of_unix_ns=None
            )
            actual = neighbor_order_expected_bytes_v1(ordered)
            # UTF-8 text file; trailing newline optional.
            expected_norm = expected_path.read_text(encoding="utf-8").strip().encode("utf-8")
            if actual != expected_norm:
                errors.append(
                    f"neighbor_order_bytes_mismatch:actual={actual!r} expected={expected_norm!r}"
                )
        else:
            errors.append("inner_edges_invalid")

    passed = len(errors) == 0
    return {
        "id": "G-P05-MG-01",
        "name": "neighbor_order_golden_bytes",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"mg_runtime_schema_version": MG_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_mg02_fingerprint_uniqueness_static() -> dict[str, Any]:
    """**G-P05-MG-02** — collision detector rejects duplicate fingerprints for distinct links."""
    errors: list[str] = []
    d = octs_multigraph_neighbor_order_fixture_dir()
    inner_path = d / "neighbor_order_inner_v1.json"
    if not inner_path.is_file():
        errors.append(f"missing_fixture:{inner_path}")
    else:
        inner = json.loads(inner_path.read_text(encoding="utf-8"))
        if isinstance(inner, dict):
            edges = inner.get("edges")
            if isinstance(edges, list):
                golden_dup = list_fs_mg01_duplicate_fingerprint_violations(edges)
                if golden_dup:
                    errors.extend(golden_dup)
            else:
                errors.append("inner_edges_not_list")
        else:
            errors.append("inner_projection_not_object")

    # Synthetic collision: two authoritative links, identical fingerprint inputs, distinct ids.
    sid = "11111111-1111-1111-1111-111111111111"
    tid = "22222222-2222-2222-2222-222222222222"
    stable = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    base_edge: dict[str, Any] = {
        "kind": "org_meaning_link",
        "link_type": "org.handle_links_canonical",
        "source_entity_id": sid,
        "target_entity_id": tid,
        "link_class": "authoritative",
        "link_authority": "authoritative",
        "confidence_class": "declared",
        "evidence_raw_record_ids": [1],
        "rule_id": None,
        "valid_from": None,
        "valid_to": None,
        "revoked_at": None,
        "supersedes_link_id": None,
        "promoted_from_candidate_id": None,
        "promotion_policy_id": None,
        "link_row_stable_id": stable,
    }
    twin_a = {**base_edge, "id": "00000000-0000-0000-0000-0000000000a1"}
    twin_b = {**base_edge, "id": "00000000-0000-0000-0000-0000000000b2"}
    synthetic_dup = list_fs_mg01_duplicate_fingerprint_violations([twin_a, twin_b])
    if not synthetic_dup:
        errors.append("expected_synthetic_fs_mg01_collision_not_detected")

    passed = len(errors) == 0
    return {
        "id": "G-P05-MG-02",
        "name": "fingerprint_uniqueness_collision_detector",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"mg_runtime_schema_version": MG_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }
