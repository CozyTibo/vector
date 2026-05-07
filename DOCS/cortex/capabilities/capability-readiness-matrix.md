# Capability Readiness Matrix

Readiness reflects architecture realism, not feature completeness.

| Capability | Required Phases | Required Primitives | Current Readiness | Major Missing Pieces |
| --- | --- | --- | --- | --- |
| Organizational Search | 01-08 | canonical entities, temporal filters, provenance-aware retrieval | Partial | retrieval relevance policy, large-scale temporal query optimization |
| Execution Intelligence | 01-09 | blockers/dependencies/ownership continuity, temporal drift metrics | Low | execution-topology analytics, continuity scoring robustness |
| Onboarding Intelligence | 01-08 | historical reconstruction, decision lineage, provenance windows | Partial | long-horizon retrieval UX, narrative synthesis guardrails |
| Incident Analysis | 01-09 | event chronology, decision/action lineage, ambiguity surfacing | Low | causality model boundaries, replay-aware incident diff tooling |
| Strategic Analysis | 01-09 | initiative topology, recurring pattern mining, confidence calibration | Low | uncertainty-aware synthesis, anti-overclaim controls |
| Delivery Reconstruction | 01-07 | cross-tool artifact chain, temporal transitions, replay comparability | Partial | scalable chain traversal and divergence diagnostics |
| Organizational Memory | 01-06 | durable raw/canonical layers, identity continuity, retention policy | Strong | memory compaction/governance policies for very long horizons |
| Dependency Intelligence | 01-09 | dependency graph, blocker propagation timeline, ownership overlays | Low | deep graph traversal economics, fragility scoring |
| Decision Lineage | 01-07 | decision nodes, evidence references, consequence linkage | Partial | ontology hardening for tradeoff and consequence classes |
| Initiative Continuity | 01-07 | initiative identity across tools/time, continuity stitching | Low | unresolved aliasing and split/merge lifecycle handling |
| Operational Debugging | 01-10 | replay controls, phase state visibility, provenance drill-down | Partial | richer operator diagnostics and replay cost controls |
| Ambiguity Investigation | 01-10 | explicit ambiguity objects, confidence/provenance views | Partial | ambiguity lifecycle policy and closure workflows |
| Replay-Driven Analysis | 01-10 | replay execution framework, version lineage, output diffs | Low | replay economics automation and generation-comparison UX |
| Historical Org Reconstruction | 01-09 | temporal snapshots, org topology reconstruction, continuity graph | Low | scalable historical state materialization and trust scoring |
| Copilot Family | 01-09 | retrieval + reasoning + synthesis over trusted memory | Low | bounded action policies, evaluation harnesses, trust calibration |

## Portfolio Observations

- Phase 01/02 maturity supports durable evidence capture but not end-state cognition by itself.
- Biggest blockers for end-state capabilities are in phases 07-09 (reasoning/retrieval/synthesis) plus temporal/linkage hardening.
- Trust gaps are less about data existence and more about explainable uncertainty handling at query/synthesis time.
