"""Phase 07 P07-09 — retrieval addressing model (**RET-ADDR-01**).

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-addressing-model.md``.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.query_contract import (
    RETRIEVAL_ADDRESSING_REF_KEYS_V1,
    RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import (
    derive_retrieval_lookup_id_v1,
    format_retrieval_lookup_id_v1,
)

PHASE07_RETRIEVAL_ADDRESSING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_CANON_VERSION_V1: Final[str] = "RETRIEVAL-CANON-1"

RETRIEVAL_INDEX_CANON_VERSION_V1: Final[str] = "RETRIEVAL-INDEX-1"

GP07_ADDR01_GATE_ID_V1: Final[str] = "G-P07-ADDR-01"

RETRIEVAL_ADDRESSING_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-addressing-model.md"
)

RET_ADDR_RESOLUTION_ORDER_V1: Final[tuple[str, ...]] = (
    "direct_retrieval_lookup_id",
    "legacy_index_causal_chain",
    "legacy_index_walk",
    "legacy_index_lineage",
    "legacy_index_materialization",
    "compose_canon_lookup_id",
)

_RETRIEVAL_ADDR_RESOLVE_FAILURES_TOTAL_V1: int = 0

_GOLDEN_V1_PATH_TAIL: Final[tuple[str, ...]] = (
    "tests",
    "vector",
    "domains",
    "cortex",
    "retrieval",
    "retrieval_golden_vectors",
    "v1",
)


@dataclass(frozen=True, slots=True)
class RetrievalAddressResolutionV1:
    retrieval_lookup_id: str
    resolution_path: str
    index_kind: str | None = None
    index_key: str | None = None
    partial_addressing: bool = False
    missing_fields: tuple[str, ...] = ()


class RetrievalAddressingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_retrieval_addressing_resolve_failures_total_v1() -> int:
    return _RETRIEVAL_ADDR_RESOLVE_FAILURES_TOTAL_V1


def record_retrieval_addressing_resolve_failure_v1(
    *,
    tenant_id: str,
    addressing: Mapping[str, Any],
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    global _RETRIEVAL_ADDR_RESOLVE_FAILURES_TOTAL_V1
    _RETRIEVAL_ADDR_RESOLVE_FAILURES_TOTAL_V1 += 1
    return {
        "event": "retrieval_addressing_resolve_failure",
        "tenant_id": tenant_id,
        "addressing": dict(addressing),
        "detail": dict(detail or {}),
    }


def normalize_temporal_scope_for_addressing_v1(
    temporal_scope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not temporal_scope:
        return {}
    out: dict[str, Any] = {}
    for key in sorted(temporal_scope):
        val = temporal_scope[key]
        if val is not None and str(val).strip():
            out[key] = val
    return out


def normalize_replay_pins_for_addressing_v1(
    replay_pins: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not replay_pins:
        return {}
    allowed = (
        "retrieval_policy_digest",
        "tcre_policy_bundle_digest",
        "octs_engine_build_ref",
        "index_epoch",
        "retrieval_replay_identity",
        "replay_identity",
        "expected_replay_identity",
        "export_sequence",
        "walk_result_hash",
    )
    return {k: replay_pins[k] for k in sorted(replay_pins) if k in allowed and replay_pins[k] is not None}


def build_retrieval_window_ref_body_v1(
    *,
    t_as_of_unix_ns: int | None = None,
    materialization_id: str | None = None,
    window_start_ns: int | None = None,
    window_end_ns: int | None = None,
    chronology_window_ref: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if chronology_window_ref:
        body["chronology_window_ref"] = str(chronology_window_ref).strip()
    if materialization_id:
        body["materialization_id"] = str(materialization_id).strip()
    if t_as_of_unix_ns is not None:
        body["t_as_of_unix_ns"] = int(t_as_of_unix_ns)
    if window_start_ns is not None and window_end_ns is not None:
        body["window_start_ns"] = int(window_start_ns)
        body["window_end_ns"] = int(window_end_ns)
    return body


def build_retrieval_chain_ref_body_v1(
    *,
    causal_chain_id: str,
    tcre_policy_bundle_digest: str | None = None,
    breakpoint_index: int | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"causal_chain_id": str(causal_chain_id).strip()}
    if tcre_policy_bundle_digest:
        body["tcre_policy_bundle_digest"] = str(tcre_policy_bundle_digest).strip()
    if breakpoint_index is not None:
        body["breakpoint_index"] = int(breakpoint_index)
    return body


def build_org_entity_ref_body_v1(*, org_entity_id: str) -> dict[str, Any]:
    return {"kind": "org_entity_ref", "org_entity_id": str(org_entity_id).strip()}


def build_org_link_ref_body_v1(*, org_link_id: str) -> dict[str, Any]:
    return {"kind": "org_link_ref", "org_link_id": str(org_link_id).strip()}


def build_retrieval_walk_ref_body_v1(
    *,
    walk_id: str,
    walk_result_hash: str | None = None,
    traversal_epoch: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"walk_id": str(walk_id).strip()}
    if walk_result_hash:
        body["walk_result_hash"] = str(walk_result_hash).strip()
    if traversal_epoch:
        body["traversal_epoch"] = str(traversal_epoch).strip()
    return body


def build_retrieval_lineage_ref_body_v1(
    *,
    artifact_kind: str,
    artifact_ref: str,
    terminal_digest: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "artifact_kind": str(artifact_kind).strip(),
        "artifact_ref": str(artifact_ref).strip(),
    }
    if terminal_digest:
        body["terminal_digest"] = str(terminal_digest).strip()
    return body


def build_retrieval_lookup_canon_body_v1(
    *,
    tenant_id: str,
    workload_class: str,
    primary_address: Mapping[str, Any],
    temporal_scope: Mapping[str, Any] | None = None,
    replay_pins: Mapping[str, Any] | None = None,
    execution_partition: str = "authoritative",
) -> dict[str, Any]:
    """``RETRIEVAL-CANON-1`` sorted JSON body for content-addressed lookup ids."""
    body: dict[str, Any] = {
        "canon_version": RETRIEVAL_CANON_VERSION_V1,
        "tenant_id": str(tenant_id),
        "workload_class": str(workload_class),
        "primary_address": dict(primary_address),
        "temporal_scope": normalize_temporal_scope_for_addressing_v1(temporal_scope),
    }
    if execution_partition == "authoritative":
        pins = normalize_replay_pins_for_addressing_v1(replay_pins)
        if pins:
            body["replay_pins"] = pins
    return body


def compute_retrieval_lookup_id_from_canon_body_v1(canon_body: Mapping[str, Any]) -> str:
    return format_retrieval_lookup_id_v1(hash_reasoning_canonical_json_sha256_v1(canon_body))


def extract_primary_address_from_addressing_v1(
    addressing: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Map envelope addressing refs → ``primary_address`` for canon lookup id."""
    if addressing.get("retrieval_window_ref") is not None:
        ref = addressing["retrieval_window_ref"]
        if isinstance(ref, dict):
            return {"kind": "retrieval_window_ref", **ref}
        return build_retrieval_window_ref_body_v1(chronology_window_ref=str(ref))
    if addressing.get("chronology_window_ref"):
        return build_retrieval_window_ref_body_v1(
            chronology_window_ref=str(addressing["chronology_window_ref"])
        )
    if addressing.get("materialization_id"):
        return build_retrieval_window_ref_body_v1(
            materialization_id=str(addressing["materialization_id"])
        )
    chain = addressing.get("retrieval_chain_ref")
    if isinstance(chain, dict):
        cid = chain.get("causal_chain_id") or chain.get("causal_chain_ref")
        if cid:
            return build_retrieval_chain_ref_body_v1(
                causal_chain_id=str(cid),
                tcre_policy_bundle_digest=chain.get("tcre_policy_bundle_digest"),
                breakpoint_index=chain.get("breakpoint_index"),
            )
    chain_id = addressing.get("causal_chain_id") or addressing.get("causal_chain_ref")
    if chain_id:
        return build_retrieval_chain_ref_body_v1(causal_chain_id=str(chain_id))
    walk = addressing.get("retrieval_walk_ref")
    if isinstance(walk, dict) and walk.get("walk_id"):
        return {
            "kind": "retrieval_walk_ref",
            **build_retrieval_walk_ref_body_v1(
                walk_id=str(walk["walk_id"]),
                walk_result_hash=walk.get("walk_result_hash"),
                traversal_epoch=walk.get("traversal_epoch"),
            ),
        }
    if addressing.get("retrieval_walk_ref") and not isinstance(walk, dict):
        return build_retrieval_walk_ref_body_v1(walk_id=str(addressing["retrieval_walk_ref"]))
    lineage = addressing.get("retrieval_lineage_ref")
    if isinstance(lineage, dict) and lineage.get("artifact_kind") and lineage.get("artifact_ref"):
        return {
            "kind": "retrieval_lineage_ref",
            **build_retrieval_lineage_ref_body_v1(
                artifact_kind=str(lineage["artifact_kind"]),
                artifact_ref=str(lineage["artifact_ref"]),
                terminal_digest=lineage.get("terminal_digest"),
            ),
        }
    if addressing.get("retrieval_lineage_ref") and addressing.get("artifact_kind"):
        return build_retrieval_lineage_ref_body_v1(
            artifact_kind=str(addressing["artifact_kind"]),
            artifact_ref=str(addressing.get("retrieval_lineage_ref") or addressing.get("artifact_ref", "")),
        )
    if addressing.get("org_entity_id"):
        return build_org_entity_ref_body_v1(org_entity_id=str(addressing["org_entity_id"]))
    if addressing.get("org_link_id"):
        return build_org_link_ref_body_v1(org_link_id=str(addressing["org_link_id"]))
    if addressing.get("retrieval_lookup_id"):
        return {"retrieval_lookup_id": str(addressing["retrieval_lookup_id"]).strip()}
    return None


def assess_partial_addressing_v1(
    addressing: Mapping[str, Any],
    *,
    workload_class: str,
) -> tuple[bool, tuple[str, ...]]:
    """Return (partial, missing_fields) when some but not all workload-primary refs present."""
    primary_by_workload: dict[str, tuple[str, ...]] = {
        "chronology_window": ("chronology_window_ref", "retrieval_window_ref", "materialization_id"),
        "materialization_as_of": ("materialization_id", "retrieval_window_ref"),
        "causal_chain": ("causal_chain_id", "causal_chain_ref", "retrieval_chain_ref"),
        "traversal_lineage": ("retrieval_walk_ref", "walk_id"),
        "replay_equivalence": ("retrieval_lookup_id", "causal_chain_id"),
        "lineage_explorer": ("retrieval_lineage_ref", "artifact_kind", "artifact_ref"),
        "ownership_continuity": ("org_entity_id", "org_link_id"),
        "dependency_propagation": ("org_entity_id", "org_link_id"),
        "continuity_topology": ("org_entity_id",),
        "escalation": ("org_link_id",),
    }
    required = primary_by_workload.get(workload_class, ("retrieval_lookup_id",))
    present = [k for k in RETRIEVAL_ADDRESSING_REF_KEYS_V1 if _ref_present_v1(addressing, k)]
    missing = [k for k in required if not _ref_present_v1(addressing, k)]
    partial = bool(present) and bool(missing)
    return partial, tuple(missing)


def _ref_present_v1(addressing: Mapping[str, Any], key: str) -> bool:
    val = addressing.get(key)
    if val is None:
        return False
    if isinstance(val, dict):
        return bool(val)
    return bool(str(val).strip())


def _replay_identity_from_envelope_v1(
    envelope: Mapping[str, Any],
    *,
    expected_replay_identity: str | None,
) -> str | None:
    pins = envelope.get("replay_pins")
    replay_pins = pins if isinstance(pins, dict) else {}
    raw = (
        expected_replay_identity
        or replay_pins.get("retrieval_replay_identity")
        or replay_pins.get("replay_identity")
        or replay_pins.get("expected_replay_identity")
    )
    return str(raw).strip() if raw else None


def resolve_retrieval_addressing_v1(
    envelope: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID | str,
    expected_replay_identity: str | None = None,
) -> RetrievalAddressResolutionV1:
    """**RET-ADDR-01** — deterministic addressing → ``retrieval_lookup_id``."""
    addressing = envelope.get("addressing")
    if not isinstance(addressing, dict):
        raise RetrievalAddressingError("addressing_required")
    wl = str(envelope.get("workload_class") or "")
    partition = str(envelope.get("execution_partition") or "authoritative")
    partial, missing = assess_partial_addressing_v1(addressing, workload_class=wl)
    replay_id = _replay_identity_from_envelope_v1(
        envelope, expected_replay_identity=expected_replay_identity
    )

    direct = addressing.get("retrieval_lookup_id")
    if direct is not None and str(direct).strip():
        lid = format_retrieval_lookup_id_v1(str(direct).strip())
        return RetrievalAddressResolutionV1(
            retrieval_lookup_id=lid,
            resolution_path="direct_retrieval_lookup_id",
            partial_addressing=partial,
            missing_fields=missing,
        )

    if replay_id:
        chain_id = addressing.get("causal_chain_id") or addressing.get("causal_chain_ref")
        if chain_id is not None and str(chain_id).strip():
            index_key = f"causal_chain:{str(chain_id).strip()}"
            return RetrievalAddressResolutionV1(
                retrieval_lookup_id=derive_retrieval_lookup_id_v1(
                    index_kind="causal_chain",
                    index_key=index_key,
                    replay_identity=replay_id,
                ),
                resolution_path="legacy_index_causal_chain",
                index_kind="causal_chain",
                index_key=index_key,
                partial_addressing=partial,
                missing_fields=missing,
            )
        walk_ref = addressing.get("retrieval_walk_ref")
        walk_id = addressing.get("walk_id")
        if isinstance(walk_ref, dict):
            walk_id = walk_ref.get("walk_id") or walk_id
        elif walk_ref and not isinstance(walk_ref, dict):
            walk_id = walk_ref
        if walk_id and str(walk_id).strip():
            index_key = f"walk:{str(walk_id).strip()}"
            return RetrievalAddressResolutionV1(
                retrieval_lookup_id=derive_retrieval_lookup_id_v1(
                    index_kind="walk",
                    index_key=index_key,
                    replay_identity=replay_id,
                ),
                resolution_path="legacy_index_walk",
                index_kind="walk",
                index_key=index_key,
                partial_addressing=partial,
                missing_fields=missing,
            )
        if addressing.get("artifact_kind") and (
            addressing.get("artifact_ref") or addressing.get("retrieval_lineage_ref")
        ):
            ref = str(addressing.get("artifact_ref") or addressing.get("retrieval_lineage_ref"))
            kind = str(addressing["artifact_kind"])
            index_key = f"lineage:{kind}:{ref}"
            return RetrievalAddressResolutionV1(
                retrieval_lookup_id=derive_retrieval_lookup_id_v1(
                    index_kind="lineage",
                    index_key=index_key,
                    replay_identity=replay_id,
                ),
                resolution_path="legacy_index_lineage",
                index_kind="lineage",
                index_key=index_key,
                partial_addressing=partial,
                missing_fields=missing,
            )
        mat = addressing.get("materialization_id")
        if mat and str(mat).strip():
            index_key = f"materialization:{str(mat).strip()}"
            return RetrievalAddressResolutionV1(
                retrieval_lookup_id=derive_retrieval_lookup_id_v1(
                    index_kind="materialization",
                    index_key=index_key,
                    replay_identity=replay_id,
                ),
                resolution_path="legacy_index_materialization",
                index_kind="materialization",
                index_key=index_key,
                partial_addressing=partial,
                missing_fields=missing,
            )
        org_ent = addressing.get("org_entity_id")
        if org_ent and str(org_ent).strip():
            index_key = f"org_entity:{str(org_ent).strip()}"
            return RetrievalAddressResolutionV1(
                retrieval_lookup_id=derive_retrieval_lookup_id_v1(
                    index_kind="org_entity",
                    index_key=index_key,
                    replay_identity=replay_id,
                ),
                resolution_path="legacy_index_org_entity",
                index_kind="org_entity",
                index_key=index_key,
                partial_addressing=partial,
                missing_fields=missing,
            )
        org_link = addressing.get("org_link_id")
        if org_link and str(org_link).strip():
            index_key = f"org_link:{str(org_link).strip()}"
            return RetrievalAddressResolutionV1(
                retrieval_lookup_id=derive_retrieval_lookup_id_v1(
                    index_kind="org_link",
                    index_key=index_key,
                    replay_identity=replay_id,
                ),
                resolution_path="legacy_index_org_link",
                index_kind="org_link",
                index_key=index_key,
                partial_addressing=partial,
                missing_fields=missing,
            )
    primary = extract_primary_address_from_addressing_v1(addressing)
    if primary and not primary.get("retrieval_lookup_id"):
        canon = build_retrieval_lookup_canon_body_v1(
            tenant_id=str(tenant_id),
            workload_class=wl,
            primary_address=primary,
            temporal_scope=envelope.get("temporal_scope")
            if isinstance(envelope.get("temporal_scope"), dict)
            else None,
            replay_pins=envelope.get("replay_pins")
            if isinstance(envelope.get("replay_pins"), dict)
            else None,
            execution_partition=partition,
        )
        return RetrievalAddressResolutionV1(
            retrieval_lookup_id=compute_retrieval_lookup_id_from_canon_body_v1(canon),
            resolution_path="compose_canon_lookup_id",
            partial_addressing=partial,
            missing_fields=missing,
        )

    record_retrieval_addressing_resolve_failure_v1(
        tenant_id=str(tenant_id),
        addressing=addressing,
        detail={"missing_fields": list(missing), "partial": partial},
    )
    raise RetrievalAddressingError(
        "addressing_unresolved",
        detail={
            "addressing": dict(addressing),
            "rd_code": RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1,
            "partial_addressing": partial,
            "missing_fields": list(missing),
        },
    )


def build_retrieval_addressing_catalog_v1() -> dict[str, Any]:
    return {
        "phase07_retrieval_addressing_runtime_schema_version": (
            PHASE07_RETRIEVAL_ADDRESSING_RUNTIME_SCHEMA_VERSION
        ),
        "canon_version": RETRIEVAL_CANON_VERSION_V1,
        "index_canon_version": RETRIEVAL_INDEX_CANON_VERSION_V1,
        "lookup_id_format": "sha256:<64 lowercase hex>",
        "resolution_order": list(RET_ADDR_RESOLUTION_ORDER_V1),
        "addressing_ref_keys": list(RETRIEVAL_ADDRESSING_REF_KEYS_V1),
        "rd_addressing_unresolved": RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1,
        "retrieval_addressing_resolve_failures_total": (
            get_retrieval_addressing_resolve_failures_total_v1()
        ),
        "doctrine_anchor": RETRIEVAL_ADDRESSING_SPEC_REF_V1,
        "gate_id": GP07_ADDR01_GATE_ID_V1,
    }


def retrieval_golden_vectors_v1_root() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        candidate = root.joinpath(*_GOLDEN_V1_PATH_TAIL)
        if candidate.is_dir():
            return candidate
        alt = root / "backend" / Path(*_GOLDEN_V1_PATH_TAIL)
        if alt.is_dir():
            return alt
    raise FileNotFoundError("retrieval_golden_vectors/v1 not found")


def load_retrieval_golden_case_v1(case_id: str) -> dict[str, Any]:
    root = retrieval_golden_vectors_v1_root()
    path = root / "cases" / case_id / "case.json"
    if not path.is_file():
        raise FileNotFoundError(f"golden case not found: {case_id}")
    loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RetrievalAddressingError("golden_case_not_object")
    return loaded


def run_retrieval_golden_addressing_case_v1(case: Mapping[str, Any]) -> dict[str, Any]:
    """Execute addressing resolution for a golden case (no DB)."""
    inputs = case.get("inputs")
    if not isinstance(inputs, dict):
        raise RetrievalAddressingError("golden_case_missing_inputs")
    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise RetrievalAddressingError("golden_case_missing_expected")
    envelope = {
        "schema_version": 1,
        "tenant_id": inputs.get("tenant_id"),
        "workload_class": inputs.get("workload_class"),
        "intent": inputs.get("intent", "inspect"),
        "execution_partition": inputs.get("execution_partition", "authoritative"),
        "addressing": dict(inputs.get("addressing") or {}),
        "temporal_scope": dict(inputs.get("temporal_scope") or {}),
        "replay_pins": dict(inputs.get("replay_pins") or {}),
    }
    res = resolve_retrieval_addressing_v1(
        envelope,
        tenant_id=str(inputs.get("tenant_id")),
        expected_replay_identity=str(inputs.get("expected_replay_identity") or "")
        or None,
    )
    out: dict[str, Any] = {
        "retrieval_lookup_id": res.retrieval_lookup_id,
        "resolution_path": res.resolution_path,
        "partial_addressing": res.partial_addressing,
    }
    exp_path = expected.get("resolution_path")
    if exp_path and res.resolution_path != exp_path:
        raise RetrievalAddressingError(
            "resolution_path_mismatch",
            detail={"expected": exp_path, "actual": res.resolution_path},
        )
    if expected.get("retrieval_lookup_id"):
        exp_lid = format_retrieval_lookup_id_v1(str(expected["retrieval_lookup_id"]))
        if res.retrieval_lookup_id != exp_lid:
            raise RetrievalAddressingError(
                "lookup_id_mismatch",
                detail={"expected": exp_lid, "actual": res.retrieval_lookup_id},
            )
    if expected.get("index_kind") and res.index_kind != expected.get("index_kind"):
        raise RetrievalAddressingError("index_kind_mismatch")
    if expected.get("index_key") and res.index_key != expected.get("index_key"):
        raise RetrievalAddressingError("index_key_mismatch")
    if "replay_identity" in expected:
        exp = expected["index_kind"], expected["index_key"], expected["replay_identity"]
        if exp[0] and exp[1] and exp[2]:
            want = derive_retrieval_lookup_id_v1(
                index_kind=str(exp[0]),
                index_key=str(exp[1]),
                replay_identity=str(exp[2]),
            )
            if res.retrieval_lookup_id != want:
                raise RetrievalAddressingError(
                    "legacy_lookup_id_mismatch",
                    detail={"expected": want, "actual": res.retrieval_lookup_id},
                )
    return out


def verify_gp07_addr01_golden_corpus_static() -> dict[str, Any]:
    errors: list[str] = []
    root = retrieval_golden_vectors_v1_root()
    manifest_path = root / "corpus_manifest.json"
    if not manifest_path.is_file():
        errors.append("missing_corpus_manifest")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("cases", []):
            if not isinstance(entry, dict):
                errors.append("invalid_manifest_case")
                continue
            case_id = entry.get("case_id")
            if not case_id:
                errors.append("manifest_case_missing_id")
                continue
            try:
                case = load_retrieval_golden_case_v1(str(case_id))
                case_gate = str(case.get("gate_id") or entry.get("gate_id") or "")
                if case_gate and case_gate != GP07_ADDR01_GATE_ID_V1:
                    continue
                run_retrieval_golden_addressing_case_v1(case)
            except (RetrievalAddressingError, FileNotFoundError) as exc:
                errors.append(f"{case_id}:{exc}")
    # determinism oracle: same inputs → same lookup id twice
    try:
        case = load_retrieval_golden_case_v1("query/causal_chain_minimal_v1")
        a = run_retrieval_golden_addressing_case_v1(case)
        b = run_retrieval_golden_addressing_case_v1(case)
        if a["retrieval_lookup_id"] != b["retrieval_lookup_id"]:
            errors.append("determinism_replay_failed")
    except (RetrievalAddressingError, FileNotFoundError) as exc:
        errors.append(f"determinism_case:{exc}")
    return {
        "id": GP07_ADDR01_GATE_ID_V1,
        "name": "gp07_addr01_golden_corpus",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors, "golden_root": str(root)},
    }
