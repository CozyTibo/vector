# Phase 04 — Linkage rule engine + versioning (P04-11)

**Status:** normative runtime spine (manifest registry + verification).  
**Role:** freeze **deterministic** linkage logic under a **versioned** manifest so candidate regeneration and replay jobs pin the same semantic contract (not ad-hoc SQL scattered across services).

---

## 1) Core objects

| Object | Meaning |
| ------ | ------- |
| **`cortex_link_rule_versions`** | Tenant-scoped **rule pack** row: `semantic_version` (operator string), `rules_manifest_json` (frozen JSON), `manifest_sha256` (canonical JSON hash), `lifecycle_state` (`active` / `deprecated`). |
| **Candidate batch pin** | Optional `cortex_org_link_candidate_batches.link_rule_version_id` referencing the row used when the batch was emitted. |

At most **one `active` row per (`tenant_id`, `semantic_version`)** (partial unique index).

---

## 2) Canonical manifest hash

`manifest_sha256 = SHA256(JSON.stringify(manifest, sort_keys=true, compact separators))`  
Recomputation on read must match stored `manifest_sha256` or verification fails (**G-P04-RULE-01** persisted half).

---

## 3) Verification — **G-P04-RULE-01**

| Half | Check |
| ---- | ----- |
| **Static** | Top-level JSON key order does not change the hash; digest length is 64 hex chars. |
| **Persisted** | No `cortex_link_rule_versions` row for the tenant has manifest/hash drift. |
| **Persisted** | No candidate batch with `link_rule_version_id` set disagrees with the pinned row (`tenant_id`, `semantic_version` vs `rule_version` string) or dangling FK. |

---

## 4) Admin + ontology

- **List:** `GET /admin/tenants/{tenant_id}/cortex/identity/link-rule-versions`  
- **Detail:** `GET /admin/tenants/{tenant_id}/cortex/identity/link-rule-versions/{rule_version_id}`  
- **Append:** `POST /admin/tenants/{tenant_id}/cortex/identity/link-rule-versions`  

Ontology pointer keys: `link_rule_version_runtime_surface_version`, `link_rule_versions_*_route`, `link_rule_version_runtime_doctrine_anchors`.

---

## 5) Replay / regen pinning

Org-link **candidate regen** jobs pass **`pinned_rule_version`**. When an **active** `cortex_link_rule_versions` row exists for that semantic string, candidate regeneration **sets** `link_rule_version_id` on the new batch (otherwise the batch remains unpinned for backward compatibility).

---

## 6) References

- `phase-04-implementation-plan.md` — Stage P04-11  
- `phase-04-control-plane-doctrine.md` — `rule_version` operator contract  
- `vector.domains.cortex.identity.linkage_rules` — runtime + gate helpers  
