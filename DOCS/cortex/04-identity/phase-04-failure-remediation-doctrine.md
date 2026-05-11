# Phase 04 — Failure + remediation (org scope) (P04-16)

**Status:** normative **org continuity failure registry** + **remediation validation ledger**, mirroring Phase **03** canonical failure/remediation patterns at tenant scope for **Identity & Linking** artifacts.

---

## 1) Persistence

| Table | Role |
| ----- | ---- |
| **`cortex_org_failure_cases`** | Append-friendly upsert keyed by **`gap_id`** (SHA-256 prefix of stable tuple); **`active`** flags operator-visible open cases. |
| **`cortex_org_remediation_validations`** | Auditable ledger of remediation attempts (**dry_run**, **confirm_execution**, **result_status**). |

---

## 2) Derived failure classes (runtime sync)

| `failure_class` | Source |
| --------------- | ------ |
| **`org_link_replay_job_failed`** | `cortex_org_link_replay_jobs.status = failed` (also recorded at failure time from replay runtime). |
| **`org_link_replay_missing_receipts`** | Completed replay job with **zero** `cortex_org_link_replay_job_receipts` rows (integrity drift vs **G-P04-RPL-01**). |
| **`org_link_temporal_overlap`** | Authoritative temporal overlap violations from link ledger scan (aggregated single active row per tenant when violations exist). |

**Sync entrypoint:** `vector.domains.cortex.identity.failure_remediation.recompute_org_derived_failure_cases` then `sync_org_failure_cases` (admin list payload).

---

## 3) Remediation classes (policy-gated)

| Class | Behavior |
| ----- | -------- |
| **`org_ambiguity_triage_ack`** | Ledger-only operator acknowledgement (no automatic graph mutation). |
| **`org_link_replay_retry`** | Invokes `execute_org_link_replay_job` with **`job_kind`** (`authoritative_replay` \| `candidate_regen`), optional **`pinned_rule_version`**, **`scope_json`**; non-dry runs require **`confirm_execution=true`**. |

---

## 4) Verification

- **G-P04-19** — **Failure registry sync completeness:** after recompute, counts of derived signals (**failed jobs**, **completed-without-receipts**, **temporal overlap presence**) match **active** rows per **`failure_class`** in **`cortex_org_failure_cases`**.

---

## 5) Admin

- `GET /admin/tenants/{tenant_id}/cortex/identity/failures`  
- `POST /admin/tenants/{tenant_id}/cortex/identity/remediation/validate`

Canonical org-agnostic routes under **`.../cortex/canonical/*`** remain unchanged.

---

## 6) Normative references

- `phase-04-implementation-plan.md` — Stage **P04-16**.  
- `phase-03-failure-degradation-doctrine.md`, `phase-03-remediation-recovery-doctrine.md` (structural precedent).  
- `vector.domains.cortex.identity.failure_remediation`.
