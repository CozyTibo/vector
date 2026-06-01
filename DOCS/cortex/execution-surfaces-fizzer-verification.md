# Execution Surfaces — Fizzer Verification

**Tenant:** `c08ef32b-f89a-40f6-9566-e19b5329436f` (Fizzer)

Run after deploy against environment with tenant data.

## Automated smoke

```bash
cd backend
export TENANT_ID=c08ef32b-f89a-40f6-9566-e19b5329436f
export ADMIN_BASE_URL=http://localhost:8000  # or prod admin origin
python scripts/execution_surfaces_smoke.py
```

## Manual acceptance

- [ ] `/cortex` opens Execution Surfaces (not Ingestion)
- [ ] ≥1 declared domain visible OR honest `no_declared_domains` advisory
- [ ] Domain detail loads with Connected Work section (chains or omission)
- [ ] Empty Conversations shows omission (not blank)
- [ ] Meetings shows `calls_not_canonized` when calls raw > 0
- [ ] Activity tab shows footnote; no “PR merged” style labels
- [ ] Domain list lifecycle filters change results
- [ ] People detail shows linked accounts
- [ ] Work artifact shows graph links or omission

## Substrate gaps (expected on Fizzer until fixed)

| Gap | Surfaces behavior |
|-----|-------------------|
| Graph backlog | `graph_expansion_incomplete` advisory |
| Calls not canonized | Meetings omission |
| Low cross-tool references | Connected work omission |
| Identity isolation | Low people participation counts |

Do not patch gaps in Execution Surfaces — fix canon, identity, graph, declared domains.
