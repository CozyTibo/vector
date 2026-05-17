# Phase 08 — Synthesis law system

**Status:** normative.  
**Registry codes:** **SD-*** (synthesis degradation / omission), **S-LEG-*** (legality predicates).

---

## §FSM — execution law

| Law ID | Text |
| ------ | ---- |
| **SYN-FSM-01** | Phases MUST execute in order; `LLM` MUST NOT run if `RETRIEVE` legality floor is `retrieval_forbidden` or `retrieval_unverifiable` (authoritative + intent≠audit). |
| **SYN-FSM-02** | `PUBLISH` MUST NOT run if `CLASSIFY` yields `synthesis_forbidden`. |
| **SYN-FSM-03** | Every phase MUST append to `execution_trace` with monotonic timestamps. |
| **SYN-FSM-04** | Idempotent job replay MUST return existing artifact when `idempotency_key` + envelope digest match. |

---

## §Legality — synthesis_legality_class (closed)

| Class | Ordinal | Authoritative usable? |
| ----- | ------- | ---------------------- |
| `synthesis_replay_safe` | 0 | Yes |
| `synthesis_degraded` | 1 | Yes (labeled) |
| `synthesis_partial` | 2 | Yes (audit/intent only) |
| `synthesis_unverifiable` | 3 | audit intent only |
| `synthesis_forbidden` | 4 | Never |

### Aggregation (S-LEG)

```
synthesis_legality = max(
  upstream_retrieval_floor,
  sd_code_floor,
  llm_schema_floor,
  replay_twin_floor
)
```

| Predicate | Maps to |
| --------- | ------- |
| **S-LEG-01** | Any hit `evidence_legality` unverifiable → floor `synthesis_unverifiable` |
| **S-LEG-02** | `SD-REPLAY-TWIN` present → floor `synthesis_degraded` |
| **S-LEG-03** | `SD-CITE-GAP` > cap → floor `synthesis_partial` |
| **S-LEG-04** | `SD-LLM-SCHEMA` after retry → `synthesis_forbidden` |
| **S-LEG-05** | Upstream `retrieval_forbidden` → `synthesis_forbidden` |
| **S-LEG-06** | Exploration partition → cap at `synthesis_partial` for authoritative consumers |
| **S-LEG-07** | `SD-UPSTREAM-RD-*` critical mass → `synthesis_degraded` |

### Fail-closed (`assert_synthesis_job_lawful_v1`)

Mirrors Phase **07**: `synthesis_unverifiable` + intent `inspect` → raise `synthesis_fail_closed`.

---

## §AI — authority and routing

### model_route registry (in policy pack)

| `model_route_id` | `authority_class` | Use |
| ---------------- | ----------------- | --- |
| `struct-v1` | `llm_structuring` | JSON claim fill |
| `narrate-v1` | `llm_narration` | discourse_only fields |
| `audit-v1` | `llm_narration` | audit intent only |

**SYN-AI-01:** Routes MUST pin `provider`, `model`, `temperature`, `max_tokens`, `response_format=json_schema`.

**SYN-AI-02:** No route may read tenant data outside provided evidence JSON.

**SYN-AI-03:** Cost ceiling per job: `max_llm_tokens` — exceed ⇒ `SD-LLM-CAP`.

---

## §Prompts — assembly law

| Law | Text |
| --- | ---- |
| **SYN-PRM-01** | Prompts assembled only from `prompt_template_id` + version + deterministic context object. |
| **SYN-PRM-02** | Context object MUST include: policy digest, hit digests sorted, omission list, claim slot plan. |
| **SYN-PRM-03** | `prompt_hash = sha256(template_version + canonical_json(context))`. |
| **SYN-PRM-04** | Operator overrides limited to `template_variant_id` enum — never raw text in authoritative partition. |

Templates live in `DOCS/cortex/synthesis/templates/` (future) or policy pack references.

---

## §Matrix — runtime legality matrix (Step 25)

`build_synthesis_legality_matrix_catalog_v1()` exports:

- Predicate list S-LEG-01..07
- Forbidden deployment combinations (e.g. production + exploration partition default)
- Histogram builders for admin

Production certification requires matrix row **PROD-SYN-01**: no tenant default workload with `synthesis_forbidden` rate > threshold.

See implementation Step **25** in sequencing plan.
