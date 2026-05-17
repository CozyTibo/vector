# Phase 08 — Anti-goals doctrine

**Status:** normative.  
**Gates:** **G-P08-ANTI-01** (forbidden cognition keys), **G-P08-ANTI-02** (import boundary), **G-P08-SCHEMA-01** (envelope algebra).

---

## Constitutional anti-goals

Phase **08** MUST NOT become:

| Anti-goal | Why forbidden |
| --------- | ------------- |
| **Chat assistant** | No session memory, no user “messages”, no turn-taking contract |
| **RAG chatbot** | Retrieval is Phase **07**; synthesis does not embed-search |
| **Freeform AI summaries** | Outputs MUST be claim+citation structured |
| **Hidden reasoning** | No chain-of-thought in operator surfaces; trace refs only |
| **Evidence fabrication** | LLM cannot introduce substrate facts |
| **Legality override** | Cannot upgrade `retrieval_unverifiable` to “safe narrative” |
| **Silent degradation** | Every gap ⇒ **SD-*** omission row |
| **Semantic ranking** | No “most relevant” re-ordering of hits |
| **Cross-phase fetch** | No direct SQL to raw/canonical/graph/TCRE tables |
| **Autonomous action** | No tickets, merges, deploys, or alerts — Phase **09** |

---

## Forbidden envelope keys (G-P08-SCHEMA-01)

Same denylist as Phase **07**, extended:

`embedding`, `embeddings`, `similarity`, `vector_search`, `semantic_search`, `natural_language_query`, `query_text`, `rag`, `rerank`, `chat`, `messages`, `conversation_id`, `tool_calls`, `agent`, `autonomous`, `recommendation`, `recommendations`, `confidence_score` (unscoped), `hidden_reasoning`, `chain_of_thought`.

Synthesis envelopes MAY include `synthesis_prompt_overrides` only as **registered template variant ids** — never raw prompt text from operators in authoritative partition.

---

## Forbidden artifact top-level keys (authoritative partition)

`answer`, `summary` (unscoped), `bullets` (unscoped), `recommendation`, `action_items` (unscoped), `hypothesis`, `prediction`, `sentiment`, `embedding`, `similarity`, `raw_llm_output` (except in `llm_trace_refs` redacted block for audit partition).

Allowed narrative containers: `claims`, `narrative_blocks[]`, each claim-backed.

---

## Import boundary (G-P08-ANTI-02)

`vector.domains.cortex.synthesis` MUST NOT import:

- `openai`, `anthropic`, `langchain`, `litellm` at module top-level in **law** packages (adapter subpackage only)
- `vector.domains.cortex.retrieval.query_execution` bypass hooks
- Phase **01–06** ORM models except through **published adapter interfaces** documented in architecture

LLM vendor SDKs live in `vector.domains.cortex.synthesis.adapters.llm` — isolated for CI mocking.

---

## AI authority ceiling

| Class | May assert substrate truth? |
| ----- | ---------------------------- |
| `orchestrator_deterministic` | Only structural aggregations |
| `llm_narration` | No — phrasing only |
| `llm_structuring` | No — JSON shape only |
| `operator_override` | Forbidden in authoritative partition |

---

## Exploration partition

Exploration synthesis jobs MUST set `non_authoritative: true` on artifacts and MUST NOT be consumed by Phase **09** default workflows (**SYN-BND-09-01**).
