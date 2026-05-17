"""Phase 07 P07-28 — **RETRIEVAL-CERT-PACK-1** + **G-P07-CLOSE-01** (closure gate).

Normative: ``DOCS/cortex/retrieval/phase-07-closure-gates-doctrine.md``,
``DOCS/cortex/retrieval/phase-07-verification-harness-spec.md`` (**G-P07-CLOSE-01**).

**FS-CG-02:** authoritative golden vector paths only under ``vectors/`` in the pack.
"""

from __future__ import annotations

import base64
import calendar
import gzip
import hashlib
import io
import json
import tarfile
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping

from vector.domains.cortex.retrieval.normative import PHASE07_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.retrieval.retrieval_addressing import retrieval_golden_vectors_v1_root
from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    load_retrieval_policy_pack_v1,
    retrieval_policy_pack_digest_v1,
    retrieval_policy_pack_fixture_path_v1,
)

PHASE07_RETRIEVAL_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1: Final[str] = "RETRIEVAL-CERT-PACK-1"

RETRIEVAL_CERT_PACK_MANIFEST_FORMAT_KEY_V1: Final[str] = "retrieval_cert_pack_format"

RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1: Final[tuple[str, ...]] = (
    "manifest.json",
    "gate_results.json",
    "vectors/manifest.json",
    "legality_matrix.json",
    "policy_pack.sha256",
)

RETRIEVAL_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/retrieval/certification-pack",
)

RETRIEVAL_ENGINE_BUILD_ID_V1: Final[str] = "retrieval.engine.stub.v1"

RETRIEVAL_CI_ARCH_VERSION_STRING_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-verification-harness-spec.md#staging-v1"
)

RETRIEVAL_CERT_PACK_TAR_MTIME: Final[int] = calendar.timegm((1980, 1, 1, 0, 0, 0, 0, 0, 0))


def _retrieval_canonical_json_obj_v1(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {str(k): _retrieval_canonical_json_obj_v1(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_retrieval_canonical_json_obj_v1(x) for x in obj]
    return obj


def retrieval_canonical_json_bytes_v1(obj: Any) -> bytes:
    """Canonical UTF-8 JSON bytes (sorted keys, NFC strings)."""
    canon = _retrieval_canonical_json_obj_v1(obj)
    return json.dumps(canon, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_retrieval_vectors_bundle_hash_v1() -> str:
    """Deterministic digest over shipped golden corpus manifest + case bodies."""
    root = retrieval_golden_vectors_v1_root()
    paths: list[Path] = [root / "corpus_manifest.json"]
    paths.extend(sorted(root.glob("cases/*/case.json"), key=lambda p: str(p).lower()))
    tenant_slice = root / "tenant_verification" / "org_graph_retrieval_slice_good_v1.json"
    if tenant_slice.is_file():
        paths.append(tenant_slice)
    entries: list[dict[str, str]] = []
    for p in paths:
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        entries.append({"path": rel, "sha256": f"sha256:{h}"})
    body = {"entries": entries}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _manifest_digest_v1(manifest: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(retrieval_canonical_json_bytes_v1(dict(manifest))).hexdigest()


def _gate_results_bytes_for_inner_digest_v1(gate_results: Mapping[str, Any]) -> bytes:
    pruned = {k: v for k, v in dict(gate_results).items() if k != "manifest_digest"}
    return retrieval_canonical_json_bytes_v1(pruned)


def _inner_payload_digest_v1(
    *,
    gate_results_bytes: bytes,
    vectors_manifest_b: bytes,
    legality_matrix_b: bytes,
    policy_pack_sha_b: bytes,
    vec_parts: list[tuple[str, bytes]],
) -> str:
    parts: list[bytes] = [
        gate_results_bytes,
        vectors_manifest_b,
        legality_matrix_b,
        policy_pack_sha_b,
    ]
    for _, blob in sorted(vec_parts, key=lambda t: t[0].encode("utf-8")):
        parts.append(blob)
    return "sha256:" + hashlib.sha256(b"".join(parts)).hexdigest()


def _add_tar_bytes(
    tf: tarfile.TarFile,
    arcname: str,
    data: bytes,
    *,
    mtime: int,
) -> None:
    ti = tarfile.TarInfo(name=arcname)
    ti.size = len(data)
    ti.mtime = mtime
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = "root"
    ti.mode = 0o644
    ti.type = tarfile.REGTYPE
    tf.addfile(ti, io.BytesIO(data))


def _build_ustar_bytes(members: list[tuple[str, bytes]], *, mtime: int) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        for arcname, data in members:
            _add_tar_bytes(tf, arcname, data, mtime=mtime)
    return buf.getvalue()


def _gzip_bytes(raw: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(raw)
    return buf.getvalue()


@dataclass(frozen=True, slots=True)
class RetrievalCertPackVerifyResultV1:
    passed: bool
    errors: tuple[str, ...]


def default_retrieval_cert_pack_legality_matrix_bytes_v1() -> bytes:
    from vector.domains.cortex.retrieval.retrieval_runtime_legality_matrix import (
        build_retrieval_runtime_legality_matrix_catalog_v1,
    )

    doc = build_retrieval_runtime_legality_matrix_catalog_v1(
        None,
        tenant_id=uuid.UUID(int=0),
    )
    return retrieval_canonical_json_bytes_v1(doc)


def default_retrieval_cert_pack_policy_pack_sha_bytes_v1() -> bytes:
    digest = retrieval_policy_pack_digest_v1(load_retrieval_policy_pack_v1())
    if not digest.startswith("sha256:"):
        digest = f"sha256:{digest}"
    return digest.encode("utf-8")


def default_retrieval_cert_pack_vector_files_v1() -> dict[str, bytes]:
    """Authoritative golden vector bytes for ``vectors/`` tree (**FS-CG-02**)."""
    root = retrieval_golden_vectors_v1_root()
    out: dict[str, bytes] = {}
    for rel in (
        "corpus_manifest.json",
        "tenant_verification/org_graph_retrieval_slice_good_v1.json",
    ):
        p = root / rel
        if p.is_file():
            out[f"vectors/{rel}"] = p.read_bytes()
    for case_path in sorted(root.glob("cases/*/case.json"), key=lambda p: str(p).lower()):
        rel = case_path.relative_to(root).as_posix()
        out[f"vectors/{rel}"] = case_path.read_bytes()
    return out


def build_retrieval_cert_pack_v1(
    *,
    gate_results: Mapping[str, Any],
    vector_files: Mapping[str, bytes],
    legality_matrix_bytes: bytes | None = None,
    policy_pack_sha256_bytes: bytes | None = None,
) -> bytes:
    """Build **RETRIEVAL-CERT-PACK-1** outer gzip bytes."""
    legality_b = legality_matrix_bytes or default_retrieval_cert_pack_legality_matrix_bytes_v1()
    policy_b = policy_pack_sha256_bytes or default_retrieval_cert_pack_policy_pack_sha_bytes_v1()

    vec_manifest_rows: list[dict[str, str]] = []
    vec_members: list[tuple[str, bytes]] = []
    for rel in sorted(vector_files.keys(), key=str):
        data = vector_files[rel]
        h = hashlib.sha256(data).hexdigest()
        vec_manifest_rows.append(
            {
                "fixture_version": "v1",
                "path": rel,
                "sha256": f"sha256:{h}",
            }
        )
        vec_members.append((rel, data))

    vectors_manifest_obj = {"vectors": vec_manifest_rows}
    vectors_manifest_bytes = retrieval_canonical_json_bytes_v1(vectors_manifest_obj)

    bundle_hash = compute_retrieval_vectors_bundle_hash_v1()
    policy_digest = retrieval_policy_pack_digest_v1()
    manifest_core: dict[str, Any] = {
        "engine_build_id": RETRIEVAL_ENGINE_BUILD_ID_V1,
        RETRIEVAL_CERT_PACK_MANIFEST_FORMAT_KEY_V1: RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
        "retrieval_ci_arch_version": RETRIEVAL_CI_ARCH_VERSION_STRING_V1,
        "retrieval_program_freeze_version": int(PHASE07_PROGRAM_FREEZE_VERSION),
        "retrieval_policy_digest": policy_digest,
        "retrieval_vectors_bundle_hash": bundle_hash,
        "vector_bundle_version": "v1",
    }

    inner_use = _inner_payload_digest_v1(
        gate_results_bytes=_gate_results_bytes_for_inner_digest_v1(gate_results),
        vectors_manifest_b=vectors_manifest_bytes,
        legality_matrix_b=legality_b,
        policy_pack_sha_b=policy_b,
        vec_parts=vec_members,
    )
    manifest = dict(sorted({**manifest_core, "payload_inner_sha256": inner_use}.items()))
    manifest_bytes = retrieval_canonical_json_bytes_v1(manifest)
    mdigest = _manifest_digest_v1(manifest)
    gr_final = {**dict(gate_results), "manifest_digest": mdigest}
    gate_results_bytes_final = retrieval_canonical_json_bytes_v1(gr_final)
    inner_check = _inner_payload_digest_v1(
        gate_results_bytes=_gate_results_bytes_for_inner_digest_v1(gr_final),
        vectors_manifest_b=vectors_manifest_bytes,
        legality_matrix_b=legality_b,
        policy_pack_sha_b=policy_b,
        vec_parts=vec_members,
    )
    if inner_check != inner_use:
        msg = "inner digest mismatch after manifest_digest bind"
        raise RuntimeError(msg)

    inner_members: list[tuple[str, bytes]] = [
        ("gate_results.json", gate_results_bytes_final),
        ("manifest.json", manifest_bytes),
        ("vectors/manifest.json", vectors_manifest_bytes),
        ("legality_matrix.json", legality_b),
        ("policy_pack.sha256", policy_b),
    ]
    inner_members.extend(vec_members)
    inner_members.sort(key=lambda t: t[0])
    tar_plain = _build_ustar_bytes(inner_members, mtime=RETRIEVAL_CERT_PACK_TAR_MTIME)
    return _gzip_bytes(tar_plain)


def verify_retrieval_cert_pack_v1(pack_gzip: bytes) -> RetrievalCertPackVerifyResultV1:
    """Verify **RETRIEVAL-CERT-PACK-1** structural law."""
    errs: list[str] = []
    try:
        raw = gzip.decompress(pack_gzip)
    except OSError as exc:
        return RetrievalCertPackVerifyResultV1(False, (f"gunzip_failed:{exc}",))

    buf = io.BytesIO(raw)
    with tarfile.open(fileobj=buf, mode="r:") as tf:
        raw_names = [n for n in tf.getnames() if tf.getmember(n).isreg()]
        sorted_names = sorted(raw_names, key=lambda n: n.encode("utf-8"))
        if raw_names != sorted_names:
            errs.append("tar_members_not_utf8_sorted")
        members: dict[str, bytes] = {}
        for n in raw_names:
            extracted = tf.extractfile(n)
            if extracted is None:
                errs.append(f"unreadable_member:{n}")
                continue
            members[n] = extracted.read()

    for r in RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1:
        if r not in members:
            errs.append(f"missing_member:{r}")

    if errs:
        return RetrievalCertPackVerifyResultV1(False, tuple(errs))

    manifest = json.loads(members["manifest.json"].decode("utf-8"))
    gate_results = json.loads(members["gate_results.json"].decode("utf-8"))
    if not isinstance(manifest, dict) or not isinstance(gate_results, dict):
        return RetrievalCertPackVerifyResultV1(False, ("manifest_or_gate_results_not_object",))

    vm_doc = json.loads(members["vectors/manifest.json"].decode("utf-8"))
    vm = vm_doc.get("vectors") if isinstance(vm_doc, dict) else None

    inner_hex = manifest.get("payload_inner_sha256")
    if not isinstance(inner_hex, str) or not inner_hex.startswith("sha256:"):
        errs.append("payload_inner_sha256_invalid")
    else:
        vec_parts_inner: list[tuple[str, bytes]] = []
        if isinstance(vm, list):
            for row in vm:
                if isinstance(row, dict) and isinstance(row.get("path"), str):
                    p = row["path"]
                    if p in members:
                        vec_parts_inner.append((p, members[p]))
        inner_exp = _inner_payload_digest_v1(
            gate_results_bytes=_gate_results_bytes_for_inner_digest_v1(gate_results),
            vectors_manifest_b=members["vectors/manifest.json"],
            legality_matrix_b=members["legality_matrix.json"],
            policy_pack_sha_b=members["policy_pack.sha256"],
            vec_parts=vec_parts_inner,
        )
        if inner_hex != inner_exp:
            errs.append("payload_inner_sha256_mismatch")

    if manifest.get(RETRIEVAL_CERT_PACK_MANIFEST_FORMAT_KEY_V1) != RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1:
        errs.append("retrieval_cert_pack_format_mismatch")

    md_expect = _manifest_digest_v1(manifest)
    md_obs = gate_results.get("manifest_digest")
    if md_obs != md_expect:
        errs.append("manifest_digest_mismatch")

    gates = gate_results.get("gates")
    if not isinstance(gates, list):
        errs.append("gates_not_array")
    else:
        gate_ids_list = [str(g.get("gate_id")) for g in gates if isinstance(g, dict)]
        if gate_ids_list != sorted(gate_ids_list, key=str):
            errs.append("gates_not_sorted_by_gate_id")
        for g in gates:
            if not isinstance(g, dict):
                errs.append("gate_row_not_object")
                continue
            if g.get("status") != "pass":
                errs.append(f"gate_not_pass:{g.get('gate_id')}")

    if not isinstance(vm, list):
        errs.append("vectors_manifest_vectors_not_array")
    else:
        for row in vm:
            if not isinstance(row, dict):
                errs.append("vector_manifest_row_not_object")
                continue
            p = row.get("path")
            exp = row.get("sha256")
            if not isinstance(p, str) or not isinstance(exp, str):
                errs.append("vector_manifest_bad_shape")
                continue
            if p not in members:
                errs.append(f"vector_missing:{p}")
                continue
            got = "sha256:" + hashlib.sha256(members[p]).hexdigest()
            if got != exp:
                errs.append(f"vector_hash_mismatch:{p}")

    legality = members.get("legality_matrix.json")
    if not legality or not legality.strip().startswith(b"{"):
        errs.append("legality_matrix_invalid")

    policy_sha = members.get("policy_pack.sha256", b"").decode("utf-8").strip()
    if not policy_sha.startswith("sha256:") or len(policy_sha) < 71:
        errs.append("policy_pack_sha256_invalid")

    fixture_digest = retrieval_policy_pack_digest_v1()
    fixture_prefixed = (
        fixture_digest
        if fixture_digest.startswith("sha256:")
        else f"sha256:{fixture_digest}"
    )
    if policy_sha != fixture_prefixed:
        errs.append("policy_pack_sha256_mismatch_fixture")

    return RetrievalCertPackVerifyResultV1(len(errs) == 0, tuple(errs))


def _close01_gate(passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    from vector.domains.cortex.retrieval.retrieval_verification_harness import (
        default_severity_for_retrieval_gate_v1,
    )

    return {
        "id": "G-P07-CLOSE-01",
        "name": "retrieval_cert_pack_closure",
        "passed": passed,
        "severity": default_severity_for_retrieval_gate_v1("G-P07-CLOSE-01"),
        "detail": dict(detail),
    }


def _gate_result_row_v1(gate_id: str, out: Mapping[str, Any]) -> dict[str, Any]:
    from vector.domains.cortex.retrieval.retrieval_verification_harness import (
        default_severity_for_retrieval_gate_v1,
    )

    passed = out.get("passed") is True
    sev = str(out.get("severity") or default_severity_for_retrieval_gate_v1(gate_id))
    status = "pass" if passed else ("skipped" if sev == "warn" else "fail")
    return dict(
        sorted(
            {
                "duration_ms": 0,
                "gate_id": gate_id,
                "status": status,
            }.items()
        )
    )


def _gate_rows_from_pr_blocking_v1(pr: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage_key in ("stage_a", "stage_b", "stage_c"):
        for item in pr.get(stage_key, []) or []:
            if not isinstance(item, dict):
                continue
            gid = str(item.get("id") or item.get("gate_id") or "")
            if gid:
                rows.append(_gate_result_row_v1(gid, item))
    return rows


def _gate_rows_from_wired_body_v1(body: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in body.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        gid = str(item.get("gate_id") or "")
        res = item.get("result") or {}
        if isinstance(res, dict) and gid:
            rows.append(_gate_result_row_v1(gid, res))
    return rows


def _run_closure_pipeline_build_pack_v1() -> tuple[bool, dict[str, Any], bytes | None]:
    """PR **A–C** + stages **D, E, Z** (skip **G-P07-CLOSE-01**), build + verify pack."""
    from vector.domains.cortex.retrieval.retrieval_verification_harness import (
        run_retrieval_gp07_pr_blocking_static_stages_v1,
        run_retrieval_gp07_wired_verification_stages_v1,
    )

    pr = run_retrieval_gp07_pr_blocking_static_stages_v1()
    if not pr.get("passed"):
        return False, {"pr_blocking": pr}, None

    extra = run_retrieval_gp07_wired_verification_stages_v1(
        ("D", "E", "Z"),
        skip_gate_ids=frozenset({"G-P07-CLOSE-01"}),
    )
    if not extra.get("passed"):
        return False, {"stages_d_e_z": extra}, None

    rows = _gate_rows_from_pr_blocking_v1(pr) + _gate_rows_from_wired_body_v1(extra)
    rows.sort(key=lambda r: r["gate_id"])
    for r in rows:
        if r["status"] != "pass":
            return False, {"non_pass_gate": r}, None

    gate_results_obj = {
        "gates": rows,
        "manifest_digest": "",
        "stages_completed": ["A", "B", "C", "D", "E", "Z"],
    }
    pack = build_retrieval_cert_pack_v1(
        gate_results=gate_results_obj,
        vector_files=default_retrieval_cert_pack_vector_files_v1(),
    )
    vr = verify_retrieval_cert_pack_v1(pack)
    if not vr.passed:
        return False, {"pack_verify_errors": list(vr.errors), "pack_bytes": len(pack)}, None
    return (
        True,
        {
            "pack_bytes": len(pack),
            "retrieval_cert_pack_format": RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
            "retrieval_cert_pack_format_literal_v1": RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
            "vector_file_count": len(default_retrieval_cert_pack_vector_files_v1()),
        },
        pack,
    )


def verify_gp07_close01_retrieval_cert_pack_shape_reference_static() -> dict[str, Any]:
    """**G-P07-CLOSE-01** (shape) — **RETRIEVAL-CERT-PACK-1** literals + five root files."""
    from vector.domains.cortex.retrieval.retrieval_verification_harness import (
        RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1,
    )

    errors: list[str] = []
    if RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1 != "RETRIEVAL-CERT-PACK-1":
        errors.append("retrieval_cert_pack_format_literal_drift")
    want_files = (
        "manifest.json",
        "gate_results.json",
        "vectors/manifest.json",
        "legality_matrix.json",
        "policy_pack.sha256",
    )
    if tuple(sorted(RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1, key=str)) != tuple(
        sorted(want_files, key=str)
    ):
        errors.append("required_root_files_tuple_drift")
    if not retrieval_policy_pack_fixture_path_v1().is_file():
        errors.append("missing_policy_pack_fixture")
    passed = len(errors) == 0
    return {
        "id": "G-P07-CLOSE-01",
        "name": "retrieval_cert_pack_shape_reference",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "retrieval_cert_pack_format_literal_v1": RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
            "required_root_files_v1": list(RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1),
            "retrieval_verification_harness_catalog_version": (
                RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1
            ),
        },
    }


def verify_gp07_close01_retrieval_cert_pack_closure_static() -> dict[str, Any]:
    """**G-P07-CLOSE-01** — wired gates green + **RETRIEVAL-CERT-PACK-1** round-trip."""
    shape = verify_gp07_close01_retrieval_cert_pack_shape_reference_static()
    if not shape.get("passed"):
        return shape
    ok, detail, _pack = _run_closure_pipeline_build_pack_v1()
    if not ok:
        return _close01_gate(False, detail)
    return _close01_gate(True, detail)


def verify_gp07_rcpk01_retrieval_cert_pack_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/retrieval/certification-pack",)
    if RETRIEVAL_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    for p in RETRIEVAL_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/retrieval/certification-pack" not in p:
            errors.append(f"path_missing_certification_pack_segment:{p}")
    return {
        "id": "P07-28-rcpk-paths",
        "name": "retrieval_certification_pack_admin_openapi_path_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def build_retrieval_certification_pack_snapshot_v1(
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    """Operator snapshot: gzip pack bytes + whole-file digest (read-only)."""
    ok, detail, pack = _run_closure_pipeline_build_pack_v1()
    tid = "" if tenant_id is None else str(tenant_id)
    if not ok or pack is None:
        return {
            "tenant_id": tid,
            "retrieval_certification_pack_runtime_schema_version": (
                PHASE07_RETRIEVAL_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION
            ),
            "retrieval_cert_pack_format": RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
            "closure_passed": False,
            "closure_detail": detail,
            "whole_file_sha256": None,
            "pack_gzip_base64": None,
            "pack_byte_length": None,
        }
    whole = hashlib.sha256(pack).hexdigest()
    return {
        "tenant_id": tid,
        "retrieval_certification_pack_runtime_schema_version": (
            PHASE07_RETRIEVAL_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION
        ),
        "retrieval_cert_pack_format": RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
        "closure_passed": True,
        "closure_detail": {"note": "operator_export_matches_closure_pipeline"},
        "whole_file_sha256": f"sha256:{whole}",
        "pack_gzip_base64": base64.b64encode(pack).decode("ascii"),
        "pack_byte_length": len(pack),
    }
