# Phase 07 — Replay equivalence (retrieval)

**Status:** normative.  
**Gate:** **G‑P07‑REPLAY‑01**.

---

## `retrieval_query_replay_identity`

Canonical JSON (sorted keys) over:

1. `RetrievalQueryEnvelopeV1` (excluding receipt fields)  
2. `retrieval_policy_digest` (sha256 of policy pack bytes)  
3. Sorted list of `(retrieval_lookup_id, upstream_digest)` for all hits  
4. Sorted list of `(retrieval_omission_class, trigger_key)` for omissions  

Output: 64-char hex sha256.

---

## Double-run law (**G‑P07‑REPLAY‑01**)

Given pinned:

- tenant_id  
- query envelope bytes  
- upstream artifact snapshots (walk records, TCRE job artifacts, index epoch)  

Two executions MUST produce:

- Identical `retrieval_query_replay_identity`  
- Identical `RetrievalQueryReceiptV1.receipt_digest`  
- Identical hit count and ordering  
- Identical omission multiset  

Mismatch → `retrieval_replay_divergence` event (observability).

---

## Async / index permutation (**G‑P07‑REPLAY‑02**)

Index build order MUST NOT affect authoritative query results when `index_epoch` and source digests are fixed (mirror OCTS L-EQ-02).

---

## Twin query class

Workload `replay_equivalence` executes double-run in one request and returns structural diff (mirror TCRE RUNTIME‑02 replay diff) — fields:

- `receipt_digest_a` / `receipt_digest_b`  
- `hit_count_mismatch`  
- `ordering_divergence`  
- `omission_multiset_delta`  

---

## Forbidden

- Time-based nondeterminism in sort keys  
- Unpinned policy digest in authoritative partition  
- Reading “latest” without `t_as_of` or epoch pin
