# Operator Workflows

## 1) Connector Failure Investigation
1. detect degraded/stalled ingestion state,
2. inspect connector runtime and checkpoint context,
3. inspect failure explanation and scope impact,
4. apply safe action (resume/recovery replay),
5. verify health recovery and trust state.

## 2) Replay Divergence Investigation
1. open replay job and divergence summary,
2. inspect changed objects and version context,
3. trace provenance to raw evidence,
4. classify expected vs anomalous divergence,
5. approve publish or quarantine scope.

## 3) Ambiguity Review Workflow
1. filter ambiguity queue by severity/confidence,
2. inspect competing interpretations and evidence,
3. accept/defer/escalate decision,
4. trigger targeted reprocessing if needed,
5. monitor ambiguity pressure trend.

## 4) Canonicalization QA Workflow
1. inspect canonical output quality metrics,
2. review mapping conflicts and extraction failures,
3. verify provenance completeness and confidence distribution,
4. run scoped replay QA check,
5. record QA verdict.

## 5) Provenance Debugging Workflow
1. select suspect output object,
2. trace lineage to raw source refs,
3. confirm transformation steps and versions,
4. detect lineage gaps,
5. trigger recovery/reprocessing where required.

## 6) Corruption Recovery Workflow
1. detect corruption signal and affected scope,
2. quarantine impacted scope,
3. run integrity and replay impact assessment,
4. execute approved recovery plan,
5. verify trust restoration criteria.

## 7) Extraction Drift Investigation
1. detect confidence/ambiguity drift trend,
2. compare versioned extraction behavior,
3. inspect sample lineage deltas,
4. decide on scoped replay/reprocessing,
5. monitor post-change trust and divergence.

## 8) Global Scheduled Polling Control
1. inspect global scheduler mode and current ingestion pressure,
2. toggle `Scheduled Polling` ON/OFF from root admin control,
3. confirm blast radius and acknowledge operational warning,
4. verify mode transition and queue dispatch behavior,
5. monitor workspace health trend after change.

## 9) Workspace Connector Manual Ingestion
1. open workspace ingestion panel and select connector,
2. review connector health/checkpoint/active run state,
3. trigger `Connector Ingestion` action with scope and mode,
4. confirm enqueue in expected queue lane,
5. monitor run progress and validate checkpoint advancement.
