# Phase 05 — Certification pack format (**OCTS-CERT-PACK-1**)

**Status:** normative — **GAP-P0-04 CLOSED**.  
**Pairs with:** `phase-05-closure-gates-doctrine.md`, `phase-05-ci-enforcement-architecture.md` (STAGE-Z), `phase-05-canonicalization-profile.md`.

---

## 1. Constitutional intent

A **certification-grade** artifact: deterministic bytes, ordered contents, verifiable digests, **no** hidden state. Auditors **MUST** reproduce all hashes from published bytes alone.

---

## 2. File identity

| Field | Value |
| ----- | ----- |
| **Media type** | `application/x-octs-cert-pack` |
| **Filename pattern** | `octs-cert-{tenant_id_or_ci}-{export_sequence}-{whole_sha256_prefix8}.octs.cer.gz` |
| **Outer encoding** | **gzip** (RFC 1952) of **USTAR tar** octets (POSIX.1-2001, **no** GNU longname / pax extended path). |
| **Inner ordering** | Tar member names sorted **ascending UTF-8** before `tarfile` write; **MUST** use **fixed modtime `1980-01-01 00:00:00 UTC`** and **uid/gid = 0** for reproducibility. |

**`whole_file_sha256`** = SHA-256 of **outer gzip file** (the bytes on disk).

---

## 3. Required tar members (paths exact)

| Path | Content type | Canonicalization |
| ---- | -------------- | ------------------ |
| `manifest.json` | UTF-8 JSON | **`OCTS-CANON-1`** |
| `gate_results.json` | UTF-8 JSON | **`OCTS-CANON-1`** |
| `vectors/manifest.json` | UTF-8 JSON | **`OCTS-CANON-1`** |
| `vectors/<sorted_relpath>.json` | UTF-8 JSON | per-vector schema |

**FORBIDDEN paths:** `..`, absolute paths, `GNU` pax blocks.

---

## 4. `manifest.json` (required keys — sorted)

| Key | Type | Meaning |
| --- | ---- | ------- |
| `engine_build_id` | string | Per `phase-05-traversal-equivalence-doctrine.md` §Engine identity |
| `octs_cert_pack_format` | string | Literal `OCTS-CERT-PACK-1` |
| `octs_ci_arch_version` | string | From `phase-05-ci-enforcement-architecture.md` header |
| `octs_program_freeze_version` | integer | `1` |
| `octs_schema_bundle_hash` | string | `sha256:` + 64 hex — Alembic heads + JSON Schema bundle digest |
| `payload_inner_sha256` | string | SHA-256 of **uncompressed tar** bytes |
| `vector_bundle_version` | string | e.g. `v1` — must match `octs_golden_vectors/v1` |

**`manifest_digest`** = `sha256:` + hex( SHA-256( `octs_canonical_json(manifest.json)` ) ) — stored **inside** `gate_results.json` under key `manifest_digest` for cross-check.

---

## 5. `gate_results.json`

Canonical object:

- `gates`: array of `{ "gate_id", "status", "duration_ms" }` sorted by `gate_id` ascending.  
- `manifest_digest`: string.  
- `stages_completed`: sorted array of stage names `["A","B","C","D"]` minimum for release.

**`status`:** `pass` | `fail` | `skipped` — **`skipped` FORBIDDEN** for `hard_fail` gates on release tags.

---

## 6. `vectors/manifest.json`

Sorted array of `{ "path", "sha256", "fixture_version" }` for every file under `vectors/` **except** `vectors/manifest.json` itself.

---

## 7. Hash boundaries

| Name | Definition |
| ---- | ---------- |
| Inner tar digest | `payload_inner_sha256` in manifest |
| Outer file digest | `whole_file_sha256` (marketing / file naming) |
| Manifest digest | `manifest_digest` |

---

## 8. Replay bundle inclusion

Directory `replay_samples/` **optional**. If present:

- Each file name `replay_samples/{walk_id}.json`.  
- **MUST** include only `exploration_mode=false` walks **OR** place under `replay_samples/excluded/` which **MUST** be ignored by **`G-P05-CLOSE-01`** authoritative check.

---

## 9. Module ownership

**Python package:** `vector.domains.cortex.traversal.certification_pack`  
**Functions:** `build_pack(...) -> bytes`, `verify_pack(bytes) -> PackVerifyResult`  
**FORBIDDEN:** cyclic imports from Phase 04 certification modules — **shape-only** copying of field names allowed.

---

## 10. Immutable closure

Tag `octs-cert-pack-v*` immutably references **one** outer `whole_file_sha256`. Mutation **MUST** use new tag.

---

## 11. Verification (`G-P05-CLOSE-01`)

1. Gunzip to tar bytes; verify `sha256(tar_bytes) == manifest.payload_inner_sha256`.  
2. Untar; verify member order constraint by re-sorting names.  
3. Verify each vector hash.  
4. Verify `manifest_digest`.  
5. Verify every required `hard_fail` gate `pass`.

---

## 12. Forbidden omissions

Missing **`gate_results.json`**, missing **`vectors/manifest.json`**, or missing **`manifest.json`** → **ILLEGAL PACK**.

---

## 13. Versioning

`OCTS-CERT-PACK-2` would switch `octs_cert_pack_format` literal and gzip → zstd if ever needed.
