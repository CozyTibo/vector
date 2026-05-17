# Phase 08 — Closure & certification gates

**Status:** normative.  
**Pack:** **SYNTHESIS-CERT-PACK-1** · **Gate:** **G-P08-CLOSE-01**

---

## FF-P08-5 completion criteria (10)

| # | Criterion |
| - | --------- |
| 1 | All Steps **1–35** doctrine **Strong** or **Frozen**; no Active P0 in gap matrix |
| 2 | `SynthesisPolicyPackV1_Default` fixture digest pinned in normative index |
| 3 | JSON schemas for job envelope + artifact in CI (**G-P08-SCHEMA-01**) |
| 4 | `execute_synthesis_job_envelope_v1` FSM complete with execution_trace |
| 5 | Substrate pipeline **phase_08_synthesis** wired + receipt |
| 6 | `publish_synthesis_epoch_v1` monotonic (**G-P08-REPLAY-02**) |
| 7 | Admin control plane surfaces **1–16** with `surface_kind` |
| 8 | Golden corpus passes **G-P08-REPLAY-01** + **G-P08-EVAL-01** |
| 9 | Tenant verification **G-P08-TVER-01** in CI |
| 10 | E2E scenario A in [`phase-08-e2e-operational-flow.md`](./phase-08-e2e-operational-flow.md) automated |

---

## G-P08-CLOSE-01

Binary gate: `run_synthesis_gp08_ci_cert_pack_artifact_v1()` returns `passed: true` only if criteria 1–10 satisfied.

Archive table: `cortex_synthesis_certification_archives` (mirror retrieval certification).

Admin:

- `GET .../synthesis/certification-pack`
- `POST .../synthesis/certification-pack/archive`

---

## Production certification (beyond CLOSE-01)

| Requirement | Gate |
| ----------- | ---- |
| Live LLM route soak | operator sign-off |
| Multi-tenant cost envelope | economics receipt |
| Pipeline phase **08** enabled in prod config | feature flag |
| Phase **09** ingress tested against published artifacts | cross-phase test |

---

## Operator closure checklist (Step 30)

Mirrors Phase **07** program closure UI:

- [ ] Synthesis health strip green for pilot tenants  
- [ ] Job debugger resolves scripted failure injections  
- [ ] Replay explorer shows twin pass on golden tenant  
- [ ] Certification pack archived with digest displayed  
- [ ] Overview synthesis stage linked  

---

## Phase 09 readiness declaration

Phase **08** closure authorizes Phase **09** coding when:

- **RET-BND-08-01** / **SYN-BND-09-01** enforced in code review  
- Sample artifacts exist for all Phase **09** workflow fixtures  
- `synthesis_publication_epoch` API stable  
