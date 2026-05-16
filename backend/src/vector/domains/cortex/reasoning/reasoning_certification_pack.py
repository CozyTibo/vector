"""Phase 06 P06-35 — **TCRE-CERT-PACK-1** + **G-P06-CLOSE-01** (closure parity with **OCTS-CERT-PACK-1**).

Normative: ``DOCS/cortex/reasoning/reasoning-verification-harness-spec.md`` §Gate catalog (**G-P06-CLOSE-01**);
``DOCS/cortex/05-traversal/phase-05-certification-pack-format.md`` (byte layout mirror — **TCRE** manifest keys).

**FS-CG-02:** authoritative vector paths only (golden-thread manifest bytes under ``vectors/``).
"""

from __future__ import annotations

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

from vector.domains.cortex.reasoning.normative import PHASE06_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.reasoning.reasoning_golden_thread_binding import reasoning_golden_vectors_v1_root
from vector.domains.cortex.traversal.certification_pack import OCTS_CERT_PACK_FORMAT_LITERAL

PHASE06_REASONING_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION: Final[int] = 1

TCRE_CERT_PACK_FORMAT_LITERAL_V1: Final[str] = "TCRE-CERT-PACK-1"
TCRE_CERT_PACK_MANIFEST_FORMAT_KEY_V1: Final[str] = "tcre_cert_pack_format"
TCRE_CERT_PACK_REQUIRED_ROOT_FILES_V1: Final[tuple[str, ...]] = (
    "manifest.json",
    "gate_results.json",
    "vectors/manifest.json",
)

REASONING_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/reasoning/certification-pack",
)

TCRE_REASONING_ENGINE_BUILD_ID_V1: Final[str] = "tcre.reasoning.stub.v1"
TCRE_CI_ARCH_VERSION_STRING_V1: Final[str] = (
    "DOCS/cortex/reasoning/reasoning-verification-harness-spec.md#staging-v1"
)

TCRE_CERT_PACK_TAR_MTIME: Final[int] = calendar.timegm((1980, 1, 1, 0, 0, 0, 0, 0, 0))


def _tcre_canonical_json_obj_v1(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {str(k): _tcre_canonical_json_obj_v1(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_tcre_canonical_json_obj_v1(x) for x in obj]
    return obj


def tcre_canonical_json_bytes_v1(obj: Any) -> bytes:
    """Canonical UTF-8 JSON bytes (sorted keys, NFC strings) — **TCRE-CANON-1** (mirrors OCTS-CANON-1)."""
    canon = _tcre_canonical_json_obj_v1(obj)
    return json.dumps(canon, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_tcre_reasoning_vectors_bundle_hash_v1() -> str:
    """Deterministic digest over shipped **golden-thread** manifest + bound case bodies."""
    root = reasoning_golden_vectors_v1_root()
    paths: list[Path] = [root / "corpus_manifest.json"]
    paths.extend(sorted(root.glob("cases/*/case.json"), key=lambda p: str(p).lower()))
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
    return "sha256:" + hashlib.sha256(tcre_canonical_json_bytes_v1(dict(manifest))).hexdigest()


def _tcre_gate_results_bytes_for_inner_digest_v1(gate_results: Mapping[str, Any]) -> bytes:
    pruned = {k: v for k, v in dict(gate_results).items() if k != "manifest_digest"}
    return tcre_canonical_json_bytes_v1(pruned)


def _inner_payload_digest_v1(
    *,
    gate_results_bytes: bytes,
    vectors_manifest_b: bytes,
    vec_parts: list[tuple[str, bytes]],
) -> str:
    parts: list[bytes] = [gate_results_bytes, vectors_manifest_b]
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
class TcreCertPackVerifyResultV1:
    passed: bool
    errors: tuple[str, ...]


def build_tcre_cert_pack_v1(
    *,
    gate_results: Mapping[str, Any],
    vector_files: Mapping[str, bytes],
) -> bytes:
    """Build **TCRE-CERT-PACK-1** outer gzip bytes (USTAR layout mirrors **OCTS-CERT-PACK-1**)."""
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
    vectors_manifest_bytes = tcre_canonical_json_bytes_v1(vectors_manifest_obj)
    vec_parts = list(vec_members)

    bundle_hash = compute_tcre_reasoning_vectors_bundle_hash_v1()
    manifest_core: dict[str, Any] = {
        "engine_build_id": TCRE_REASONING_ENGINE_BUILD_ID_V1,
        TCRE_CERT_PACK_MANIFEST_FORMAT_KEY_V1: TCRE_CERT_PACK_FORMAT_LITERAL_V1,
        "tcre_ci_arch_version": TCRE_CI_ARCH_VERSION_STRING_V1,
        "tcre_program_freeze_version": int(PHASE06_PROGRAM_FREEZE_VERSION),
        "tcre_reasoning_vectors_bundle_hash": bundle_hash,
        "vector_bundle_version": "v1",
    }

    inner_use = _inner_payload_digest_v1(
        gate_results_bytes=_tcre_gate_results_bytes_for_inner_digest_v1(gate_results),
        vectors_manifest_b=vectors_manifest_bytes,
        vec_parts=vec_parts,
    )
    manifest = dict(sorted({**manifest_core, "payload_inner_sha256": inner_use}.items()))
    manifest_bytes = tcre_canonical_json_bytes_v1(manifest)
    mdigest = _manifest_digest_v1(manifest)
    gr_final = {**dict(gate_results), "manifest_digest": mdigest}
    gate_results_bytes_final = tcre_canonical_json_bytes_v1(gr_final)
    inner_check = _inner_payload_digest_v1(
        gate_results_bytes=_tcre_gate_results_bytes_for_inner_digest_v1(gr_final),
        vectors_manifest_b=vectors_manifest_bytes,
        vec_parts=vec_parts,
    )
    if inner_check != inner_use:
        msg = "inner digest mismatch after manifest_digest bind"
        raise RuntimeError(msg)

    inner_members: list[tuple[str, bytes]] = [
        ("gate_results.json", gate_results_bytes_final),
        ("manifest.json", manifest_bytes),
        ("vectors/manifest.json", vectors_manifest_bytes),
    ]
    inner_members.extend(vec_members)
    inner_members.sort(key=lambda t: t[0])
    tar_plain = _build_ustar_bytes(inner_members, mtime=TCRE_CERT_PACK_TAR_MTIME)
    return _gzip_bytes(tar_plain)


def verify_tcre_cert_pack_v1(pack_gzip: bytes) -> TcreCertPackVerifyResultV1:
    """Verify **TCRE-CERT-PACK-1** structural law (mirrors **OCTS-CERT-PACK-1** §11 checks)."""
    errs: list[str] = []
    try:
        raw = gzip.decompress(pack_gzip)
    except OSError as exc:
        return TcreCertPackVerifyResultV1(False, (f"gunzip_failed:{exc}",))

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
    required = TCRE_CERT_PACK_REQUIRED_ROOT_FILES_V1
    for r in required:
        if r not in members:
            errs.append(f"missing_member:{r}")

    if errs:
        return TcreCertPackVerifyResultV1(False, tuple(errs))

    manifest = json.loads(members["manifest.json"].decode("utf-8"))
    gate_results = json.loads(members["gate_results.json"].decode("utf-8"))
    if not isinstance(manifest, dict) or not isinstance(gate_results, dict):
        return TcreCertPackVerifyResultV1(False, ("manifest_or_gate_results_not_object",))

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
            gate_results_bytes=_tcre_gate_results_bytes_for_inner_digest_v1(gate_results),
            vectors_manifest_b=members["vectors/manifest.json"],
            vec_parts=vec_parts_inner,
        )
        if inner_hex != inner_exp:
            errs.append("payload_inner_sha256_mismatch")

    if manifest.get(TCRE_CERT_PACK_MANIFEST_FORMAT_KEY_V1) != TCRE_CERT_PACK_FORMAT_LITERAL_V1:
        errs.append("tcre_cert_pack_format_mismatch")

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

    return TcreCertPackVerifyResultV1(len(errs) == 0, tuple(errs))


def default_tcre_cert_pack_vector_files_v1() -> dict[str, bytes]:
    root = reasoning_golden_vectors_v1_root()
    data = (root / "corpus_manifest.json").read_bytes()
    return {"vectors/corpus_manifest.json": data}


def verify_gp06_close01_tcre_cert_pack_shape_reference_static() -> dict[str, Any]:
    """**G-P06-CLOSE-01** (shape) — **TCRE-CERT-PACK-1** literals + required root tuple vs **OCTS-CERT-PACK-1**."""
    from vector.domains.cortex.reasoning.reasoning_verification_harness import (
        REASONING_VERIFICATION_HARNESS_CATALOG_VERSION_V1,
        default_severity_for_reasoning_gate_v1,
    )

    errors: list[str] = []
    if OCTS_CERT_PACK_FORMAT_LITERAL != "OCTS-CERT-PACK-1":
        errors.append("octs_cert_pack_format_literal_drift")
    if TCRE_CERT_PACK_FORMAT_LITERAL_V1 != "TCRE-CERT-PACK-1":
        errors.append("tcre_cert_pack_format_literal_drift")
    if TCRE_CERT_PACK_MANIFEST_FORMAT_KEY_V1 == "octs_cert_pack_format":
        errors.append("tcre_manifest_key_must_not_alias_octs_key")
    if tuple(sorted(TCRE_CERT_PACK_REQUIRED_ROOT_FILES_V1, key=str)) != tuple(
        sorted(("manifest.json", "gate_results.json", "vectors/manifest.json"), key=str)
    ):
        errors.append("required_root_files_tuple_drift")
    passed = len(errors) == 0
    return {
        "id": "G-P06-CLOSE-01",
        "name": "tcre_cert_pack_shape_reference",
        "passed": passed,
        "severity": default_severity_for_reasoning_gate_v1("G-P06-CLOSE-01"),
        "detail": {
            "errors": errors,
            "octs_cert_pack_format_literal": OCTS_CERT_PACK_FORMAT_LITERAL,
            "tcre_cert_pack_format_literal_v1": TCRE_CERT_PACK_FORMAT_LITERAL_V1,
            "tcre_cert_pack_manifest_format_key_v1": TCRE_CERT_PACK_MANIFEST_FORMAT_KEY_V1,
            "required_root_files_v1": TCRE_CERT_PACK_REQUIRED_ROOT_FILES_V1,
            "reasoning_verification_harness_catalog_version": REASONING_VERIFICATION_HARNESS_CATALOG_VERSION_V1,
        },
    }


def _close01_gate(passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    from vector.domains.cortex.reasoning.reasoning_verification_harness import (
        default_severity_for_reasoning_gate_v1,
    )

    return {
        "id": "G-P06-CLOSE-01",
        "name": "tcre_cert_pack_closure",
        "passed": passed,
        "severity": default_severity_for_reasoning_gate_v1("G-P06-CLOSE-01"),
        "detail": dict(detail),
    }


def _run_pr_e_z_build_pack_v1() -> tuple[bool, dict[str, Any], bytes | None]:
    """Run PR + **E** + **Z** (skip **G-P06-CLOSE-01**), build + verify **TCRE-CERT-PACK-1** bytes."""
    from vector.domains.cortex.reasoning.reasoning_verification_harness import (
        default_severity_for_reasoning_gate_v1,
        run_reasoning_gp06_pr_blocking_static_stages_v1,
        run_reasoning_gp06_wired_verification_stages_v1,
    )

    pr = run_reasoning_gp06_pr_blocking_static_stages_v1()
    if not pr.get("passed"):
        return False, {"pr_blocking": pr}, None

    e_body = run_reasoning_gp06_wired_verification_stages_v1(("E",))
    if not e_body.get("passed"):
        return False, {"stage_e": e_body}, None

    z_body = run_reasoning_gp06_wired_verification_stages_v1(
        ("Z",),
        skip_gate_ids=frozenset({"G-P06-CLOSE-01"}),
    )
    if not z_body.get("passed"):
        return False, {"stage_z_preclose": z_body}, None

    rows: list[dict[str, Any]] = []
    for block in (pr, e_body, z_body):
        for item in block.get("results", []) or []:
            gid = str(item.get("gate_id") or "")
            res = item.get("result") or {}
            passed = res.get("passed") is True
            sev = str(res.get("severity") or default_severity_for_reasoning_gate_v1(gid))
            status = "pass" if passed else ("skipped" if sev == "warn" else "fail")
            rows.append(
                dict(
                    sorted(
                        {
                            "duration_ms": 0,
                            "gate_id": gid,
                            "status": status,
                        }.items()
                    )
                )
            )

    rows.sort(key=lambda r: r["gate_id"])
    for r in rows:
        if r["status"] != "pass":
            return (
                False,
                {
                    "non_pass_gate": r,
                    "pr_results_len": len(pr.get("results", [])),
                },
                None,
            )

    gate_results_obj = {
        "gates": rows,
        "manifest_digest": "",
        "stages_completed": ["A", "B", "C", "D", "E", "Z"],
    }
    pack = build_tcre_cert_pack_v1(
        gate_results=gate_results_obj,
        vector_files=default_tcre_cert_pack_vector_files_v1(),
    )
    vr = verify_tcre_cert_pack_v1(pack)
    if not vr.passed:
        return False, {"pack_verify_errors": list(vr.errors), "pack_bytes": len(pack)}, None
    return True, {"pack_bytes": len(pack), "tcre_cert_pack_format": TCRE_CERT_PACK_FORMAT_LITERAL_V1}, pack


def verify_gp06_close01_tcre_cert_pack_closure_static() -> dict[str, Any]:
    """**G-P06-CLOSE-01** — PR **A–D** + **E** + **Z** (except self) green; **TCRE-CERT-PACK-1** round-trip."""
    shape = verify_gp06_close01_tcre_cert_pack_shape_reference_static()
    if not shape.get("passed"):
        return shape

    ok, detail, _pack = _run_pr_e_z_build_pack_v1()
    if not ok:
        return _close01_gate(False, detail)
    return _close01_gate(True, detail)


def build_reasoning_certification_pack_snapshot_v1(
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    """Operator snapshot: gzip pack bytes + whole-file digest (read-only)."""
    import base64

    ok, detail, pack = _run_pr_e_z_build_pack_v1()
    tid = "" if tenant_id is None else str(tenant_id)
    if not ok or pack is None:
        return {
            "tenant_id": tid,
            "reasoning_certification_pack_runtime_schema_version": (
                PHASE06_REASONING_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION
            ),
            "tcre_cert_pack_format": TCRE_CERT_PACK_FORMAT_LITERAL_V1,
            "closure_passed": False,
            "closure_detail": detail,
            "whole_file_sha256": None,
            "pack_gzip_base64": None,
            "pack_byte_length": None,
        }

    whole = hashlib.sha256(pack).hexdigest()
    return {
        "tenant_id": tid,
        "reasoning_certification_pack_runtime_schema_version": (
            PHASE06_REASONING_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION
        ),
        "tcre_cert_pack_format": TCRE_CERT_PACK_FORMAT_LITERAL_V1,
        "closure_passed": True,
        "closure_detail": {"note": "operator_export_matches_closure_pipeline"},
        "whole_file_sha256": f"sha256:{whole}",
        "pack_gzip_base64": base64.b64encode(pack).decode("ascii"),
        "pack_byte_length": len(pack),
    }


def verify_gp06_rcpk01_reasoning_cert_pack_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/reasoning/certification-pack",)
    if REASONING_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    for p in REASONING_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/reasoning/certification-pack" not in p:
            errors.append(f"path_missing_certification_pack_segment:{p}")
    return {
        "id": "P06-35-rcpk-paths",
        "name": "reasoning_certification_pack_admin_openapi_path_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
