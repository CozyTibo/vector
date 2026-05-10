# Phase 04 — Hostile Continuity Mock Dataset Strategy

**Status:** normative for **mock / dev / fixture** design — complements Phase 04 runtime doctrine; **not** production data policy.  
**Audience:** mock connector authors, Phase 04 implementers, verification/CI authors.  
**Goal:** Make the mock tenant a **deliberately messy, explainable continuity stress lab** so identity/linkage assumptions are tested **before** runtime and operator UI harden.

**Non-goals:** Random noise; realistic-looking demo that hides ambiguity; Phase 09 product narratives.

**Upstream implementation surface:** `backend/mock_connectors/` (`company_generator.py`, `fixtures/*`, per-connector `dataset_generator.py`, `unified.py`, `scripts/generate_dataset.py`).  
**Related strategy:** `DOCS/strategy/local-mock-connectors-and-fixtures.md`, `DOCS/strategy/mock-data-seed-audit.md`.

---

## 1) Principles

| Principle | Meaning |
| --------- | ------- |
| **Deterministic** | Same `seed` + same scenario slice → same identities, emails, events, and collision patterns (use stable IDs derived from seed + scenario key, not `random()` without seed binding). |
| **Explainable** | Every ambiguity has a **documented cause** (scenario id + fixture row id); operators/tests can answer “why is this contested?” |
| **Hostile, not noisy** | Collisions are **authored** to stress merges, personas, temporal validity, and replay — not accidental hash clashes. |
| **Cross-tool coherent** | The same human appears under **intentionally inconsistent** handles/emails across GitHub / Slack / Linear / Notion / Calls — by design. |
| **Governance pressure** | Data must force **candidate vs authoritative** separation: many cases MUST NOT auto-merge under default policy. |
| **Replay-sensitive** | Scenarios include **version pins**, **missing evidence**, and **supersession** so L-class drift is reproducible. |

---

## 2) Fixture taxonomy

### 2.1 Scenario families (`scenario_family_id`)

Stable string ids for generators and docs (prefix `P04MD-` = Phase 04 mock dataset).

| Family id | Intent |
| --------- | ------ |
| `P04MD-H01` | Personal GitHub + work Slack + company Linear (email/handle mismatch) |
| `P04MD-H02` | Multiple emails per human (personal, old domain, company, noreply) |
| `P04MD-H03` | Nickname vs legal name across tools |
| `P04MD-H04` | Renamed provider identities (GitHub login change, Slack display change) |
| `P04MD-H05` | Shared machine / shared git email → two humans |
| `P04MD-H06` | Same first name collision (“two Alex”) |
| `P04MD-H07` | Contractor / external consultant (partial tool presence) |
| `P04MD-H08` | Deleted / tombstoned account; historical refs survive |
| `P04MD-H09` | Service/bot vs human confusion (human commits via bot, or bot attributed as human) |
| `P04MD-H10` | Executive / founder multi-domain + personal GitHub |
| `P04MD-T01` | Identity split over time (same Slack user id → different legal mapping epoch) |
| `P04MD-T02` | Merge reversal / compensating split narrative |
| `P04MD-T03` | Overlapping ownership windows (contention) |
| `P04MD-T04` | Historical alias drift (old handle referenced years later) |
| `P04MD-X01` | Slack text references GitHub nickname only (no email) |
| `P04MD-X02` | GitHub repo transfer (org rename / transfer) |
| `P04MD-X03` | Linear issue references stale repo identifier |
| `P04MD-X04` | Notion page mentions deprecated handles |
| `P04MD-X05` | Call transcript nickname-only mentions |
| `P04MD-X06` | Multi-workspace Slack merged tenant (same company, two workspace ids) |
| `P04MD-P01` | WorkEpisode with incomplete evidence |
| `P04MD-P02` | One PR in multiple competing WorkEpisodes |
| `P04MD-P03` | CoordinationThread ambiguously tied to two initiatives |
| `P04MD-P04` | EscalationChain crossing contractor/internal boundary |
| `P04MD-P05` | DeliveryAttempt on renamed repo |
| `P04MD-P06` | ReviewCycle / BlockageEpisode with conflicting assignees |
| `P04MD-A01` | Unresolved personas (no safe merge) |
| `P04MD-A02` | Competing candidate merges |
| `P04MD-A03` | Orphaned normalized refs |
| `P04MD-A04` | Conflicting OwnershipWindow |
| `P04MD-A05` | Primitive contention |
| `P04MD-A06` | Bundle equivalence gap (cross-bundle edge without declaration) |
| `P04MD-R01` | Rule version change → candidate set shift |
| `P04MD-R02` | Evidence removed / raw tombstone |
| `P04MD-R03` | Stale canonical pointer after remap |
| `P04MD-R04` | Revoked merge / superseded link |
| `P04MD-R05` | Cross-bundle mismatch |
| `P04MD-R06` | Missing normalized ref family |
| `P04MD-R07` | Primitive replay mismatch |

### 2.2 Artifact kinds

Each scenario **emits** concrete rows across: `github.*`, `slack.*`, `linear.*`, `notion.*`, `calls.*`, and optional **`continuity_fixture`** metadata blob (see §6) for Phase 04 tests only.

---

## 3) Deterministic seed scenarios

### 3.1 Seed contract

- **Global seed** `VECTOR_MOCK_SEED` (existing) selects **base** Nexora layout.  
- **Phase 04 slice:** `P04_CONTINUITY_SCENARIO` (env or fixture file) selects **which scenario blocks** merge into the dataset (default: `hostile_full` = all families; CI may use `ci_min` = subset).  
- **Per-scenario sub-seed** `hash(seed, scenario_family_id)` drives stable user ids and emails so reordering scenarios does not reshuffle unrelated users.

### 3.2 Authoritative scenario matrix (minimum bar)

| scenario_key | Families | Primary stress |
| ------------ | -------- | -------------- |
| `nexora_p04_hostile_baseline` | H01–H10, T01–T04, X01–X06, P01–P06, A01–A06, R01–R07 | Full lab |
| `nexora_p04_ci_slice_identity` | H01,H02,H05,H06,H08, A01, R01,R04 | Fast CI |
| `nexora_p04_ci_slice_temporal` | T01,T02,T03, R04 | Temporal + merge |
| `nexora_p04_ci_slice_cross_tool` | X01,X02,X03, A03 | Refs + orphans |
| `nexora_p04_ci_slice_primitives` | P01–P05, A05, R07 | Primitives + contention |
| `nexora_p04_ci_slice_bundle` | A06, R05, R06 | Bundle equivalence |

Implementers: register scenario keys in `mock_connectors/fixtures/cortex_capability_scenarios.py` (or dedicated `phase04_continuity_scenarios.py`) and surface via `/admin/scenarios`.

---

## 4) Mock tenant personas (authored characters)

These are **named fixtures** (not random). Each row is reproducible from seed.

| persona_key | GitHub | Slack | Linear | Email(s) | Stress |
| ----------- | ------ | ----- | ------ | -------- | ------ |
| `tibo_fracture` | `darkvoid666` | display “Tibo”, handle `tibo` | `thibault@company.com` | `tibo.personal@gmail.com` on commits | H01, H02, X01 |
| `sam_carter_fracture` | `s4mmy` | “Sam” | “Samuel Carter” | personal + company | H03, H06 |
| `alex_mercer` | `alex-mercer-dev` | “Alex” | Alex Mercer | company | H06 (pair 1) |
| `alex_vasquez` | `alexvzq` | “Alex” | Alex Vasquez | company | H06 (pair 2) |
| `contractor_jules` | sparse / external | “Jules (External)” | Jules | personal only | H07, P04 |
| `shared_email_pair` | `dev1` / `dev2` | distinct | distinct | **same** `shared-bench@nexora.test` | H05 |
| `renamed_riley` | login **before** `rileycodes` **after** `riley-nexora` | display name change event | email stable | H04 |
| `split_identity_morgan` | one mapping epoch | Slack user stable | Linear person **reassigned** mid-timeline | T01 |
| `deleted_dana` | account **tombstoned** after T0; PRs/commits **before** deletion reference Dana | messages remain | issues remain | H08 |
| `bot_human_blur` | `nexora-ci[bot]` vs human `jamie` with **mixed** trailer | — | — | H09 |
| `founder_freya` | personal GH | company Slack | old-domain + new-domain email | H10, H02 |

**Rule:** Personas are **cross-linked** in content: Slack messages and PR bodies reference `darkvoid666`, `@s4mmy`, “Alex”, “Jules”, old repo paths, etc.

---

## 5) Org continuity stress matrix

Rows: **scenario** → **expected Phase 04 outcome** (post-runtime).

| Area | Mock pressure | Expected system posture (not auto-truth) |
| ---- | ------------- | ---------------------------------------- |
| Org handles | Many personas per human | Multiple handles or explicit ambiguity until merge |
| Persona bindings | Temporal + provider id changes | Intervals + supersession; never silent overwrite |
| Merges | Competing evidence | Merge queue; policy gates |
| Ambiguity queue | All H*, T*, X* families | Non-empty `ambiguity-queue` for hostile seeds |
| Candidate links | Rule-generated edges | Candidate layer populated; promotion rare |
| Authoritative links | Only after ledger writes | Small set unless test explicitly promotes |
| Replay | Pin rule version + raw manifest | Deterministic regen hash; drift injectors |
| Temporal validity | Overlaps, reversals | Validity intervals + compensating events |
| Cross-tool | Nickname mentions | Orphan refs + candidate pressure |
| Primitives | Overlapping evidence | Contention records |
| Bundle equiv | Two bundle scopes | **A06** forces declaration or blocked edge |
| Operator console | All cards | Non-zero drift/orphans/ambiguity on hostile seed |

---

## 6) Generator architecture guidance

### 6.1 Layering

1. **Base company** — existing `company_generator.py` (Nexora scale targets).  
2. **Continuity overlay** — new module e.g. `fixtures/phase04_continuity_fixtures.py`:
   - Declarative **persona table** + **event timeline** (JSON-serializable).
   - Functions `apply_phase04_scenarios(dataset: dict, seed: int, scenario_keys: list[str]) -> dict` that **mutate** or **append** users, repos, messages, issues, commits, transcript lines.
3. **Connector-specific shapers** — ensure GitHub commit `author`/`committer` emails, Slack `user` profiles, Linear `User` blobs, Notion rich text, Calls participant names **reflect** the same persona fractures.

### 6.2 `continuity_fixture` sidecar (recommended)

Optional top-level key in dataset JSON:

```json
{
  "continuity_fixture": {
    "schema_version": "phase04_mock_fixture_v1",
    "seed": 42,
    "scenario_keys": ["nexora_p04_hostile_baseline"],
    "expectations": [
      {
        "scenario_family_id": "P04MD-H01",
        "persona_key": "tibo_fracture",
        "expected_ambiguity_classes": ["unresolved_personas", "cross_tool_collision"],
        "must_not_auto_merge": true,
        "replay_drift_injectors": []
      }
    ]
  }
}
```

Phase 04 tests read **expectations** to assert queue population without scraping full JSON payloads.

### 6.3 Determinism rules

- No unseeded RNG for continuity overlay.  
- IDs: `sha256(f"{seed}:{scenario_key}:{persona_key}:{role}")` truncated per connector format.  
- Timestamps: **anchored** `T0 = now - SIMULATION_DAYS` (existing) + **fixed offsets** per scenario (e.g. rename at T0+30d).

### 6.4 Validation

Extend `scripts/validate_mock_dataset.py` to assert:

- Hostile scenarios present minimum counts (e.g. ≥2 “Alex”, ≥1 shared email pair).  
- Deleted user still referenced in historical events.  
- Repo transfer: old `full_name` appears in **historical** PR payload, new name in **current** repo object.

---

## 7) Multi-tool identity collision fixtures (detail)

### 7.1 H01 — Personal GitHub + work Slack + company Linear (canonical “tibo” story)

- **GitHub:** user `darkvoid666`; commits use `tibo.personal@gmail.com`.  
- **Slack:** profile “Tibo”, handle `tibo`, **no** email visible in mock API subset (or different email).  
- **Linear:** `thibault@company.com`, display name “Thibault Hagler”.  
- **Cross refs:** Slack thread: “Can @darkvoid666 review?”; Linear issue links PR from `darkvoid666`.  
- **Expectation:** strong **candidate** co-reference signals; **no** authoritative human merge without operator; ambiguity class **unresolved_personas** / **cross_tool_collision**.

### 7.2 H05 — Shared git email

- Two distinct humans in Slack/Linear; both commit with `shared-bench@nexora.test`.  
- **Expectation:** persona binding ambiguity; possible **forbidden** auto-link from email alone; merge queue **high_blocked** without extra evidence.

### 7.3 H06 — Two “Alex”

- Distinct surnames in Linear; GitHub logins differ; Slack both “Alex”.  
- **Expectation:** display-name collision; ambiguity **duplicate_human_display_name**; primitive assignment confusion in P02.

### 7.4 H08 — Deleted Dana

- User active in window W1; **tombstone** event W2; historical PRs, Slack exports, Linear comments still cite Dana’s ids.  
- **Expectation:** tombstone handle + read-only historical links; **G-P04-11** style behavior under doctrine.

---

## 8) Replay + ambiguity scenarios

### 8.1 Ambiguity pressure (populates operator queues)

| Injector | Queue / card |
| -------- | ------------- |
| Unmerged personas (H01, H07) | Ambiguity Queue |
| Competing merges (A02) | Merge Queue + Ambiguity |
| Orphaned refs (A03, X*) | Orphaned refs **card** + Ambiguity |
| Ownership overlap (T03, A04) | Ambiguity + Link ledger filter `ambiguous` |
| Primitive contention (A05, P02) | Ambiguity + Primitive explorer |
| Bundle gap (A06) | Bundle equivalence gaps **card** |
| Replay drift (R*) | Replay console + Link filter `replay_drift` |

### 8.2 Regeneration narrative

1. Run candidate regen at **rule_version v1** → hash **H1**.  
2. Apply injector **R01** (rule v2) → regen hash **H2 ≠ H1**.  
3. Authoritative ledger unchanged until promotion — **two-layer** replay story.

---

## 9) Primitive / org-shaped cases

| Scenario | Evidence pattern | Contention |
| -------- | ---------------- | ---------- |
| P01 | Single Slack thread + partial PR list | Incomplete WorkEpisode |
| P02 | Same PR linked from two issue threads | Two episodes claim same PR |
| P03 | Thread mentions two Linear initiatives | CoordinationThread ambiguous |
| P04 | Escalation from contractor channel to internal on-call | Boundary crossing |
| P05 | Deploy workflow on repo **after** transfer | DeliveryAttempt + renamed repo |
| P06 | Review requested from “Alex” (ambiguous) | ReviewCycle + BlockageEpisode conflict |

Primitive envelopes (Phase 3.5) should be **emitted** in fixture metadata or derived consistently in tests once runtime exists.

---

## 10) Temporal continuity edge cases

| Id | Mechanism |
| -- | --------- |
| T01 | Export Slack/Linear user mapping changelog: same `slack_user_id` tied to two `persona_key` epochs with `valid_from`/`valid_to`. |
| T02 | Merge ledger: `merge_record` then **compensating split** record (append-only). |
| T03 | Two `OwnershipWindow` rows overlapping for same `scope` with different handles. |
| T04 | Old GitHub handle referenced in 90-day-old commit; new handle in new events — alias drift. |

---

## 11) Merge governance stress cases

| Case | Data setup | Expected operator story |
| ---- | ---------- | ------------------------ |
| G1 | H01 + operator temptation to “just merge” | UI shows **policy_satisfied=false** until dual evidence |
| G2 | A02 two candidate merges for same handle pair | Merge queue **risk_class=high_blocked** |
| G3 | Contractor H07 | Merge to internal human **blocked** by default policy |
| G4 | T02 compensating split | Merge history shows **non-delete** correction |

---

## 12) Bundle equivalence edge cases

| Case | Setup | Stress |
| ---- | ------- | ------ |
| B1 | Same raw event materialized under **stub bundle A** vs **stub bundle B** in test harness | Cross-bundle canonical pointer pair without declaration |
| B2 | Explicit `cortex_bundle_equivalence_declaration` in fixture optional table (future) | Positive path for authorized cross-bundle link |

Mock dataset **simulates** bundle id labels in `continuity_fixture.expectations` until DB exists.

---

## 13) Orphaned references

Produce normalized refs (Phase 3.5 families) that **deliberately** have no org link:

- Slack message mentioning `@unknown_vendor_bot`.  
- Notion link to `github.com/old-org/old-repo`.  
- Linear issue `repository` field stale after **X02** transfer.  
- Call transcript “ask Sam” with no resolved surname.

**Expectation:** Orphan refs **card** > 0 on hostile seed; ambiguity rows **conflicting_refs**.

---

## 14) Replay drift scenarios — L-class catalog (deterministic)

Normative **example** codes for mock + verification (align with `phase-04-continuity-replay-doctrine.md` when written).

| Code | Cause | Fixture injector |
| ---- | ----- | ---------------- |
| **L0** | Clean regen — baseline | None |
| **L1** | Link rule version changed | R01 — bump `cortex_link_rule_version` pin |
| **L2** | Evidence missing (raw deleted / filtered) | R02 — remove raw row from replay manifest |
| **L3** | Stale canonical pointer | R03 — canonical id from old bundle scope |
| **L4** | Authoritative link revoked / superseded | R04 — `revoked_at` set on prior link |
| **L5** | Cross-bundle without equivalence | R05 — A06 data path |
| **L6** | Normalized ref family missing | R06 — strip ref family from payload |
| **L7** | Primitive evidence mismatch | R07 — change evidence multiset for primitive |

Each injector documents **expected** receipt fields and **deterministic** hash delta vs baseline.

---

## 15) Expected operator console population (hostile seed)

When Phase 04 admin is implemented, **`nexora_p04_hostile_baseline`** should **typically** yield:

| Surface | Non-trivial expectation |
| ------- | ------------------------ |
| Identity Dashboard | Ambiguous identities > 0; candidate links > authoritative; orphaned refs > 0; bundle gaps > 0 (if bundle labels present) |
| Handles | Multiple rows per “obvious” human story (until merges) |
| Link Ledger | Mix of candidate/authoritative; filters exercised |
| Merge Queue | At least one **pending** high-risk proposal |
| Ambiguity Queue | Multiple classes represented |
| Primitives | At least one **contention** row |
| Replay | Completed + **drift** jobs in L1–L7 slices |
| Export preview | Stable counts; no traversal UI |

---

## 16) Replay / regeneration test fixtures

| Test slice | Scenario keys | Asserts |
| ---------- | ------------- | ------- |
| `test_p04_regen_determinism` | `ci_slice_identity` | Same seed → same candidate hash (L0) |
| `test_p04_regen_rule_bump` | + R01 | L1 receipt; hash changes predictably |
| `test_p04_authoritative_replay` | `ci_slice_temporal` | Ledger replay reproduces link set hash |
| `test_p04_merge_compensation` | T02 | No illegal delete; history shows split |
| `test_p04_bundle_block` | `ci_slice_bundle` | Forbidden cross-bundle link without declaration |

---

## 17) Suggested CI fixture slices

| Job | `P04_CONTINUITY_SCENARIO` | Time budget |
| --- | ------------------------- | ----------- |
| PR fast | `nexora_p04_ci_slice_identity` | < 30s mock gen |
| Nightly | `nexora_p04_hostile_baseline` | full |

CI must **not** rely on production connectors; use mock server + frozen `dataset.json` optional artifact for ultra-stable jobs.

---

## 18) Implementation checklist (mock codebase)

- [ ] Add `fixtures/phase04_continuity_fixtures.py` (personas + timeline + injectors).  
- [ ] Wire `apply_phase04_scenarios` from `company_generator.build_dataset` behind env flag `VECTOR_MOCK_PHASE04_HOSTILE=true` or scenario key.  
- [ ] Extend GitHub commits / Slack messages / Linear issues / Notion blocks / Calls transcripts for scenarios **X01–X05**.  
- [ ] Add `continuity_fixture` block to exported dataset.  
- [ ] Update `validate_mock_dataset.py` for hostile invariants.  
- [ ] Document scenario keys in mock `README.md`.  
- [ ] When Phase 04 runtime exists: ingest + replay tests consume **same** scenario keys.

---

## References

- `phase-04-implementation-plan.md` — program stages; mock alignment **P04-20** / verification **P04-15**  
- `phase-04-control-plane-doctrine.md` — operator surfaces populated by this data  
- `phase-04-normative-index.md`  
- `backend/mock_connectors/README.md`  
- `DOCS/strategy/mock-data-seed-audit.md`  
