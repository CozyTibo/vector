"""Deterministic replay fingerprints (drift detection surfaces, no hidden equivalence)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")


def fingerprint_topology_edges(edges: list[dict[str, Any]] | None) -> str:
    pairs = sorted(
        {
            (
                int(e["parent_raw_record_id"]),
                int(e["child_raw_record_id"]),
            )
            for e in (edges or [])
            if isinstance(e, dict)
            and e.get("parent_raw_record_id") is not None
            and e.get("child_raw_record_id") is not None
        }
    )
    return hashlib.sha256(_canonical_json_bytes({"edges": pairs})).hexdigest()


def fingerprint_id_order(raw_record_ids: list[int]) -> str:
    return hashlib.sha256(_canonical_json_bytes([int(x) for x in raw_record_ids])).hexdigest()


def fingerprint_lineage_from_receipts(receipts: list[dict[str, Any]]) -> str:
    """Hash divergence classes + payload hashes declared on receipts (oracle-visible only)."""
    rows: list[dict[str, Any]] = []
    for r in receipts:
        if not isinstance(r, dict):
            continue
        dj = r.get("detail_json") if isinstance(r.get("detail_json"), dict) else {}
        rows.append(
            {
                "raw_record_id": int(r.get("raw_record_id") or 0),
                "divergence_class": str(r.get("divergence_class") or ""),
                "raw_payload_hash": dj.get("raw_payload_hash"),
            }
        )
    rows.sort(key=lambda x: x["raw_record_id"])
    return hashlib.sha256(_canonical_json_bytes(rows)).hexdigest()


def fingerprint_materialization_writes(
    *,
    writes_applied: int,
    writes_skipped: int,
    counts_by_divergence_class: dict[str, int],
) -> str:
    payload = {
        "writes_applied": int(writes_applied),
        "writes_skipped": int(writes_skipped),
        "counts": {k: int(counts_by_divergence_class.get(k, 0) or 0) for k in sorted(counts_by_divergence_class.keys())},
    }
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def build_replay_fingerprint_bundle(
    *,
    topology: dict[str, Any],
    process_order: list[int],
    receipt_dicts: list[dict[str, Any]],
    writes_applied: int,
    writes_skipped: int,
    counts_by_divergence_class: dict[str, int],
) -> dict[str, Any]:
    return {
        "topology_edge_fp": fingerprint_topology_edges(topology.get("dependency_edges")),
        "process_order_fp": fingerprint_id_order(process_order),
        "lineage_receipt_fp": fingerprint_lineage_from_receipts(receipt_dicts),
        "materialization_outcome_fp": fingerprint_materialization_writes(
            writes_applied=writes_applied,
            writes_skipped=writes_skipped,
            counts_by_divergence_class=counts_by_divergence_class,
        ),
        "dependency_graph_fp": hashlib.sha256(
            _canonical_json_bytes(
                {
                    "cycle": bool(topology.get("cycle_detected")),
                    "orphan_n": len(topology.get("orphan_refs") or []),
                    "edge_n": len(topology.get("dependency_edges") or []),
                    "max_depth": int(topology.get("max_replay_depth") or 0),
                }
            )
        ).hexdigest(),
    }
