"""Phase 05 P05-10 — hop receipt contract (**RULE HR-01/02**, **FS-HR-01..03**).

Normative: ``DOCS/cortex/05-traversal/phase-05-hop-receipt-doctrine.md``.
Fingerprint law: ``multigraph_model.compute_edge_fingerprint_v1`` (**MG**).
Observed / derived: ``observed_vs_derived`` (**OVD**).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, cast

from vector.domains.cortex.traversal.multigraph_model import (
    MultigraphModelError,
    compute_edge_fingerprint_v1,
)
from vector.domains.cortex.traversal.observed_vs_derived import (
    PROVENANCE_CLASS_DERIVED,
    PROVENANCE_CLASS_OBSERVED,
    ObservedDerivedInvariantError,
    validate_hop_receipt_observed_derived,
    validate_hop_receipt_sequence,
)
from vector.domains.cortex.traversal.walk_diagnostics_contract import (
    WalkDiagnosticsContractError,
    validate_skip_reason_enum_v1,
)

HR_RUNTIME_SCHEMA_VERSION: Final[int] = 1


class HopReceiptContractError(ValueError):
    """Raised when hop receipts violate hop receipt doctrine."""


def _repo_root_with_oct_schemas() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = (
            root
            / "DOCS"
            / "cortex"
            / "05-traversal"
            / "schemas"
            / "octs-walk-request-v1.schema.json"
        )
        if marker.is_file():
            return root
    msg = "Could not locate DOCS/cortex/05-traversal/schemas from hop_receipt_contract."
    raise RuntimeError(msg)


def octs_hop_receipt_fixture_dir() -> Path:
    """Directory holding **G-P05-HR-01** / **G-P05-HR-02** hop receipt golden vectors."""
    root = _repo_root_with_oct_schemas()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "hop_receipts"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"hop_receipts golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def _non_empty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def stated_edge_fingerprint_from_receipt(receipt: Mapping[str, Any]) -> str | None:
    """Return ``authority_binding.edge_fingerprint`` when present."""
    ab = receipt.get("authority_binding")
    if not isinstance(ab, dict):
        return None
    fp = ab.get("edge_fingerprint")
    if isinstance(fp, str) and fp.startswith("sha256:") and len(fp) == 71:
        return fp
    return None


def extract_evidence_envelope_v1(receipt: Mapping[str, Any]) -> dict[str, Any] | None:
    """Envelope for **FS-HR-02** — nested ``evidence_envelope`` or flat ``authority_binding``."""
    ab = receipt.get("authority_binding")
    if not isinstance(ab, dict):
        return None
    nested = ab.get("evidence_envelope")
    if isinstance(nested, dict):
        return cast(dict[str, Any], dict(nested))
    required = (
        "org_link_id",
        "link_type",
        "source_node_id",
        "target_node_id",
        "validity_half_open",
    )
    if all(k in ab for k in required):
        return {
            "org_link_id": ab["org_link_id"],
            "link_type": ab["link_type"],
            "source_node_id": ab["source_node_id"],
            "target_node_id": ab["target_node_id"],
            "validity_half_open": ab["validity_half_open"],
            "bundle_scope_id": ab.get("bundle_scope_id"),
        }
    return None


def envelope_to_inner_edge_for_fingerprint_v1(env: Mapping[str, Any]) -> dict[str, Any]:
    """Map doctrine **evidence envelope** fields to multigraph inner-edge shape."""
    vh = env.get("validity_half_open")
    if not isinstance(vh, dict):
        msg = "evidence_envelope.validity_half_open must be an object"
        raise HopReceiptContractError(msg)
    org = env.get("org_link_id")
    if not _non_empty_str(org):
        msg = "evidence_envelope.org_link_id must be a non-empty string"
        raise HopReceiptContractError(msg)
    for k in ("link_type", "source_node_id", "target_node_id"):
        if not _non_empty_str(env.get(k)):
            msg = f"evidence_envelope.{k} must be a non-empty string"
            raise HopReceiptContractError(msg)
    return {
        "bundle_scope_id": env.get("bundle_scope_id"),
        "link_row_stable_id": str(org),
        "link_type": str(env["link_type"]),
        "source_entity_id": str(env["source_node_id"]),
        "target_entity_id": str(env["target_node_id"]),
        "valid_from": vh.get("valid_from"),
        "valid_to": vh.get("valid_to"),
    }


def recomputed_edge_fingerprint_from_receipt_v1(receipt: Mapping[str, Any]) -> str:
    """Recompute **edge_fingerprint** from envelope fields (**FS-HR-02**)."""
    env = extract_evidence_envelope_v1(receipt)
    if env is None:
        msg = "hop_receipt missing evidence envelope fields for fingerprint law"
        raise HopReceiptContractError(msg)
    inner = envelope_to_inner_edge_for_fingerprint_v1(env)
    try:
        return compute_edge_fingerprint_v1(inner)
    except MultigraphModelError as exc:
        msg = f"fingerprint input invalid: {exc}"
        raise HopReceiptContractError(msg) from exc


def list_fs_hr03_derived_org_link_without_derivation_rule_violations(
    receipt: Mapping[str, Any],
) -> list[str]:
    """**FS-HR-03** — derived receipt with ``org_link_id`` but no ``derivation_rule_id``."""
    if receipt.get("provenance_class") != PROVENANCE_CLASS_DERIVED:
        return []
    ab = receipt.get("authority_binding")
    if not isinstance(ab, dict):
        return []
    oid = ab.get("org_link_id")
    if not _non_empty_str(oid):
        return []
    if not _non_empty_str(receipt.get("derivation_rule_id")):
        return ["fs_hr03:derived_with_org_link_id_requires_derivation_rule_id"]
    return []


def list_hr02_same_fingerprint_different_sequence_violations(
    hop_receipts: Sequence[Mapping[str, Any]],
    *,
    allow_revisit_vertices: bool,
) -> list[str]:
    """**RULE HR-02** — same stated fingerprint at two sequences unless revisit allowed."""
    if allow_revisit_vertices:
        return []
    pairs: list[tuple[int, str]] = []
    for r in hop_receipts:
        seq = r.get("hop_sequence")
        fp = stated_edge_fingerprint_from_receipt(r)
        if isinstance(seq, int) and isinstance(fp, str):
            pairs.append((seq, fp))
    errors: list[str] = []
    for i, (s1, f1) in enumerate(pairs):
        for s2, f2 in pairs[i + 1 :]:
            if f1 == f2 and s1 != s2:
                errors.append(f"hr02:same_fingerprint_at_sequences_{s1}_and_{s2}")
    return errors


def _org_link_id_from_receipt_for_dangling(receipt: Mapping[str, Any]) -> str | None:
    env = extract_evidence_envelope_v1(receipt)
    if env is not None and _non_empty_str(env.get("org_link_id")):
        return str(env["org_link_id"]).strip()
    ab = receipt.get("authority_binding")
    if isinstance(ab, dict) and _non_empty_str(ab.get("org_link_id")):
        return str(ab["org_link_id"]).strip()
    return None


def validate_hop_receipt_list_contract_v1(
    hop_receipts: Sequence[Mapping[str, Any]],
    *,
    pinned_org_link_ids: frozenset[str] | None,
    allow_dangling_evidence_refs: bool,
    allow_revisit_vertices: bool,
) -> None:
    """Validate a hop receipt list (HR + OVD + FS-HR + HR-02 cross-sequence).

    Raises:
        HopReceiptContractError: on violation.
    """
    if not hop_receipts:
        return
    try:
        validate_hop_receipt_sequence(hop_receipts)
    except ObservedDerivedInvariantError as exc:
        raise HopReceiptContractError(str(exc)) from exc

    for i, rec in enumerate(hop_receipts):
        try:
            validate_hop_receipt_observed_derived(rec)
        except ObservedDerivedInvariantError as exc:
            raise HopReceiptContractError(f"hop[{i}]: {exc}") from exc
        v = list_fs_hr03_derived_org_link_without_derivation_rule_violations(rec)
        if v:
            raise HopReceiptContractError(f"hop[{i}]: " + "; ".join(v))

        if "skip_reason" in rec and rec.get("skip_reason") is not None:
            try:
                validate_skip_reason_enum_v1(rec.get("skip_reason"))
            except WalkDiagnosticsContractError as exc:
                raise HopReceiptContractError(f"hop[{i}]: {exc}") from exc

        pc = rec.get("provenance_class")
        if pc == PROVENANCE_CLASS_OBSERVED:
            if stated_edge_fingerprint_from_receipt(rec) is None:
                msg = f"hop[{i}]: FS-HR-01 observed hop missing edge_fingerprint"
                raise HopReceiptContractError(msg)
            try:
                expected = recomputed_edge_fingerprint_from_receipt_v1(rec)
            except HopReceiptContractError as exc:
                raise HopReceiptContractError(f"hop[{i}]: {exc}") from exc
            stated = stated_edge_fingerprint_from_receipt(rec)
            if stated != expected:
                msg = (
                    f"hop[{i}]: FS-HR-02 fingerprint mismatch stated={stated!r} "
                    f"recomputed={expected!r}"
                )
                raise HopReceiptContractError(msg)

        elif pc == PROVENANCE_CLASS_DERIVED:
            stated_der = stated_edge_fingerprint_from_receipt(rec)
            if stated_der is not None:
                expected_der = recomputed_edge_fingerprint_from_receipt_v1(rec)
                if stated_der != expected_der:
                    msg = (
                        f"hop[{i}]: FS-HR-02 fingerprint mismatch stated={stated_der!r} "
                        f"recomputed={expected_der!r}"
                    )
                    raise HopReceiptContractError(msg)

        if (
            not allow_dangling_evidence_refs
            and pinned_org_link_ids is not None
            and pc == PROVENANCE_CLASS_OBSERVED
        ):
            oid = _org_link_id_from_receipt_for_dangling(rec)
            if oid is not None and oid not in pinned_org_link_ids:
                msg = f"hop[{i}]: dangling evidence org_link_id not in pinned projection: {oid!r}"
                raise HopReceiptContractError(msg)

    bad = list_hr02_same_fingerprint_different_sequence_violations(
        hop_receipts,
        allow_revisit_vertices=allow_revisit_vertices,
    )
    if bad:
        raise HopReceiptContractError("RULE HR-02: " + "; ".join(bad))


def validate_hop_receipt_list_for_hash_body_v1(hop_receipts: Sequence[Any]) -> None:
    """Subset for ``walk_result`` **hash_body** — no pinned projection (dangling not enforced)."""
    if not isinstance(hop_receipts, list):
        return
    rows = [cast(Mapping[str, Any], x) for x in hop_receipts if isinstance(x, dict)]
    if not rows:
        return
    validate_hop_receipt_list_contract_v1(
        rows,
        pinned_org_link_ids=None,
        allow_dangling_evidence_refs=True,
        allow_revisit_vertices=False,
    )


def verify_gp05_hr01_fingerprint_recompute_from_envelope_static() -> dict[str, Any]:
    """**G-P05-HR-01** — golden observed receipt envelope recomputes to stated fingerprint."""
    errors: list[str] = []
    d = octs_hop_receipt_fixture_dir()
    path = d / "hop_receipt_observed_good_v1.json"
    if not path.is_file():
        errors.append(f"missing_fixture:{path}")
        return {
            "id": "G-P05-HR-01",
            "name": "hop_receipt_fingerprint_recompute",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"hr_runtime_schema_version": HR_RUNTIME_SCHEMA_VERSION, "errors": errors},
        }
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        errors.append("fixture_not_object")
    else:
        try:
            validate_hop_receipt_list_contract_v1(
                [raw],
                pinned_org_link_ids=None,
                allow_dangling_evidence_refs=True,
                allow_revisit_vertices=False,
            )
        except HopReceiptContractError as exc:
            errors.append(f"good_fixture_rejected:{exc}")
        bad = dict(raw)
        ab = dict(bad["authority_binding"])
        ab["edge_fingerprint"] = "sha256:" + "0" * 64
        bad["authority_binding"] = ab
        try:
            validate_hop_receipt_list_contract_v1(
                [bad],
                pinned_org_link_ids=None,
                allow_dangling_evidence_refs=True,
                allow_revisit_vertices=False,
            )
        except HopReceiptContractError:
            pass
        else:
            errors.append("expected_bad_fingerprint_fixture_to_fail")

    passed = len(errors) == 0
    return {
        "id": "G-P05-HR-01",
        "name": "hop_receipt_fingerprint_recompute",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"hr_runtime_schema_version": HR_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_hr02_dangling_org_link_rejected_static() -> dict[str, Any]:
    """**G-P05-HR-02** — dangling observed org link fails when policy disallows dangling."""
    errors: list[str] = []
    d = octs_hop_receipt_fixture_dir()
    bundle_path = d / "hop_receipt_dangling_bundle_v1.json"
    if not bundle_path.is_file():
        errors.append(f"missing_fixture:{bundle_path}")
        return {
            "id": "G-P05-HR-02",
            "name": "hop_receipt_dangling_evidence",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"hr_runtime_schema_version": HR_RUNTIME_SCHEMA_VERSION, "errors": errors},
        }
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        errors.append("bundle_not_object")
    else:
        pinned_raw = bundle.get("pinned_org_link_ids")
        dangling = bundle.get("dangling_receipt")
        good = bundle.get("good_receipt")
        if not isinstance(pinned_raw, list) or not all(isinstance(x, str) for x in pinned_raw):
            errors.append("pinned_org_link_ids_invalid")
        elif not isinstance(dangling, dict):
            errors.append("dangling_receipt_invalid")
        elif not isinstance(good, dict):
            errors.append("good_receipt_invalid")
        else:
            pinned = frozenset(str(x) for x in pinned_raw)
            try:
                validate_hop_receipt_list_contract_v1(
                    [good],
                    pinned_org_link_ids=pinned,
                    allow_dangling_evidence_refs=False,
                    allow_revisit_vertices=False,
                )
            except HopReceiptContractError as exc:
                errors.append(f"unexpected_good_rejection:{exc}")
            try:
                validate_hop_receipt_list_contract_v1(
                    [dangling],
                    pinned_org_link_ids=pinned,
                    allow_dangling_evidence_refs=False,
                    allow_revisit_vertices=False,
                )
            except HopReceiptContractError:
                pass
            else:
                errors.append("expected_dangling_receipt_to_fail")

    passed = len(errors) == 0
    return {
        "id": "G-P05-HR-02",
        "name": "hop_receipt_dangling_evidence",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"hr_runtime_schema_version": HR_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }
