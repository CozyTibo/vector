# Celery Beat — single leader verification

Production runs **one** Beat process on the **cortex worker** ECS service (`vector-substrate-worker-service` task family). Beat must not run on ingestion workers or API replicas.

## Verify (prod)

```bash
# Exactly one running task should include celery beat in its containers
aws ecs list-tasks --cluster vector-prod --service-name vector-substrate-worker-service --desired-status RUNNING

# Task definition should list worker + celery-beat containers
aws ecs describe-task-definition --task-definition vector-substrate-worker
```

## Verify (local)

`docker compose` service `celery-beat` is separate from `celery-worker`; only start **one** `celery-beat` instance.

## Failure modes

| Symptom | Cause |
|---------|--------|
| Duplicate scheduled passes | Two Beat leaders — scale beat sidecar to one task |
| No ticks | Beat container down; check cortex worker service events |
| Ticks but no passes | Cortex **worker** container not consuming `vector` / pass queues |

After deploy, confirm `canon_scheduler_ticks` / `identity_scheduler_ticks` / `ingestion_scheduler_ticks` receive new rows every interval.
