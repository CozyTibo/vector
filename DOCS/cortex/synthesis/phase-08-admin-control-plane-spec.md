# Phase 08 — Admin & control plane specification

**Status:** normative operator spec.  
**RBAC:** `10-admin/admin-permissions-model.md`, dangerous actions: `10-admin/dangerous-action-safety-model.md`.

---

## surface_kind (mandatory on every response)

| surface_kind | Used for |
| ------------ | -------- |
| `runtime_backed` | Jobs, artifacts, receipts, metrics, audit log |
| `doctrine_catalog` | Policy packs, workload registry, gate catalog |
| `derived_aggregate` | Histograms, lag, coverage rollups |
| `verification_probe` | G-P08-* harness output |

---

## §Surfaces (mandatory at closure)

| # | Surface | surface_kind | Operator answers |
| - | ------- | ------------ | ---------------- |
| 1 | **Synthesis health strip** | runtime_backed | Is synthesis replay-safe? Publication epoch? Job failure rate? |
| 2 | **Coverage panel** | derived_aggregate | eligible scopes vs synthesized vs published |
| 3 | **Policy pack inspector** | doctrine_catalog | Active `synthesis_policy_pack_digest`, caps, model routes |
| 4 | **Job debugger** | runtime_backed | Why this job failed / degraded |
| 5 | **Artifact explorer** | runtime_backed | Claims, legality, publication state |
| 6 | **Citation / evidence trace** | runtime_backed | Per-claim → retrieval hit → provenance |
| 7 | **Synthesis provenance** | runtime_backed | Receipt embed, retrieval replay id |
| 8 | **Synthesis legality explorer** | derived_aggregate | S-LEG predicates + histogram |
| 9 | **Synthesis degradation explorer** | derived_aggregate | SD-* counts + upstream RD-* |
| 10 | **Synthesis replay explorer** | runtime_backed | Twin diff, structural vs wording |
| 11 | **Evaluation explorer** | verification_probe | G-P08-EVAL-* quality metrics |
| 12 | **LLM trace inspector** | runtime_backed | prompt_hash, model_route (redacted content in prod) |
| 13 | **Pipeline synthesis panel** | runtime_backed | Phase **08** on substrate run detail |
| 14 | **Throughput / latency** | derived_aggregate | job duration, token usage, queue depth |
| 15 | **Certification view** | verification_probe | SYNTHESIS-CERT-PACK-1 status |
| 16 | **Control plane aggregate** | derived_aggregate | Queue depth, workload histogram, economics |

---

## §Workflows

### W1 — Debug “why is synthesis empty?”

1. Job debugger → job id from pipeline receipt  
2. RETRIEVE phase → retrieval sub-query receipts  
3. SD-* explorer → `SD-SCOPE-EMPTY` vs `SD-CITE-GAP`  
4. Cross-link Phase **07** query debugger (prefilled envelope)

### W2 — Verify replay before Phase 09 enablement

1. Run `replay_equivalence_synthesis` job  
2. Replay explorer → structural twin pass  
3. Legality explorer → S-LEG green  
4. Certification view → G-P08-CLOSE-01 badge

### W3 — Force re-synthesis (dangerous)

1. Scope: tenant + `retrieval_lookup_id` + epoch pins  
2. Confirmation phrase: `RE-SYNTHESIZE {tenant_slug}`  
3. Expected: new artifact, new digest, publication epoch bump  

### W4 — Recovery after phase 08 failure

1. Pipeline run detail → phase **08** `failed`  
2. Inspect `SD-PIPELINE-GAP` vs `SD-LLM-*`  
3. Retry: `POST .../synthesis/jobs/retry` OR re-run pipeline from **07** if index stale  

---

## §RBAC permissions

| Permission | Capability |
| ---------- | ---------- |
| `cortex.synthesis.read` | All GET surfaces |
| `cortex.synthesis.job.run` | Create jobs (scoped) |
| `cortex.synthesis.publish` | Manual publish barrier |
| `cortex.synthesis.replay` | Twin + replay explorer |
| `cortex.synthesis.dangerous` | Force re-synth, skip, purge artifacts |

---

## §HTTP routes (admin API)

| Method | Path | surface_kind |
| ------ | ---- | ------------ |
| GET | `/admin/tenants/{id}/cortex/synthesis/control-plane` | derived_aggregate |
| GET | `/admin/tenants/{id}/cortex/synthesis/health` | runtime_backed |
| POST | `/admin/tenants/{id}/cortex/synthesis/jobs/run` | runtime_backed |
| GET | `/admin/tenants/{id}/cortex/synthesis/jobs/{job_id}` | runtime_backed |
| GET | `/admin/tenants/{id}/cortex/synthesis/artifacts` | runtime_backed |
| GET | `/admin/tenants/{id}/cortex/synthesis/artifacts/{artifact_id}` | runtime_backed |
| POST | `/admin/tenants/{id}/cortex/synthesis/artifacts/{id}/verify-replay` | verification_probe |
| GET | `/admin/tenants/{id}/cortex/synthesis/omissions` | derived_aggregate |
| GET | `/admin/tenants/{id}/cortex/synthesis/degradation` | derived_aggregate |
| GET | `/admin/tenants/{id}/cortex/synthesis/legality-matrix` | doctrine_catalog |
| GET | `/admin/tenants/{id}/cortex/synthesis/evaluation` | verification_probe |
| GET | `/admin/tenants/{id}/cortex/synthesis/certification-pack` | verification_probe |
| POST | `/admin/tenants/{id}/cortex/synthesis/certification-pack/archive` | verification_probe |
| GET | `/admin/catalog/cortex/synthesis/policy-pack` | doctrine_catalog |

---

## §SPA routes

| Route | Page |
| ----- | ---- |
| `.../cortex/synthesis` | Overview + health strip |
| `.../cortex/synthesis/jobs` | Job list + debugger |
| `.../cortex/synthesis/artifacts/:id` | Artifact + citations |
| `.../cortex/synthesis/replay` | Replay explorer |
| `.../cortex/synthesis/control-plane` | Aggregate |
| `.../cortex/synthesis/certification` | Closure pack |

Nav: enabled when tenant `synthesis_runtime_legality` allows (matrix PROD-SYN-01).

---

## §Overview integration

Substrate overview pipeline stage **`synthesis`**:

| Field | Source |
| ----- | ------ |
| `status` | completeness projection |
| `coverage_percent` | synthesized / eligible |
| `publication_epoch` | `cortex_synthesis_publication_epochs` |
| `lag_vs_retrieval` | epoch diff |
| `sd_critical_count` | degradation rollup |

Link: “Open Synthesis control plane” → SPA route.

---

## §Doctrine vs runtime labeling

UI MUST render badge:

- **Live truth** — `runtime_backed`, `derived_aggregate`, `verification_probe`  
- **Spec catalog** — `doctrine_catalog` (read-only, may differ from tenant runtime until pack loaded)

Never present doctrine catalog metrics as tenant operational truth.
