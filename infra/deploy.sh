#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

set -a
# shellcheck source=env/production.env
source "${SCRIPT_DIR}/env/production.env"
set +a

: "${AWS_REGION:?set AWS_REGION in infra/env/production.env}"
: "${AWS_ACCOUNT_ID:?set AWS_ACCOUNT_ID in infra/env/production.env}"
: "${ECS_CLUSTER_NAME:?set ECS_CLUSTER_NAME in infra/env/production.env}"
: "${ECS_SERVICE_BACKEND:?set ECS_SERVICE_BACKEND in infra/env/production.env}"
: "${ECS_SERVICE_WORKER:?set ECS_SERVICE_WORKER in infra/env/production.env}"

TMP="${TMPDIR:-/tmp}"
TASK_BE="$(mktemp "${TMP}/vector-backend-task.XXXXXX.json")"
TASK_WR="$(mktemp "${TMP}/vector-worker-task.XXXXXX.json")"
trap 'rm -f "${TASK_BE}" "${TASK_WR}"' EXIT

sed -e "s/884953290372/${AWS_ACCOUNT_ID}/g" -e "s/eu-west-1/${AWS_REGION}/g" \
  "${SCRIPT_DIR}/ecs/backend-task.json" > "${TASK_BE}"
sed -e "s/884953290372/${AWS_ACCOUNT_ID}/g" -e "s/eu-west-1/${AWS_REGION}/g" \
  "${SCRIPT_DIR}/ecs/worker-task.json" > "${TASK_WR}"

BACKEND_REV="$(aws ecs register-task-definition --cli-input-json "file://${TASK_BE}" --query 'taskDefinition.revision' --output text --region "${AWS_REGION}")"
WORKER_REV="$(aws ecs register-task-definition --cli-input-json "file://${TASK_WR}" --query 'taskDefinition.revision' --output text --region "${AWS_REGION}")"

aws ecs update-service \
  --cluster "${ECS_CLUSTER_NAME}" \
  --service "${ECS_SERVICE_BACKEND}" \
  --task-definition "vector-backend:${BACKEND_REV}" \
  --force-new-deployment \
  --region "${AWS_REGION}"

aws ecs update-service \
  --cluster "${ECS_CLUSTER_NAME}" \
  --service "${ECS_SERVICE_WORKER}" \
  --task-definition "vector-worker:${WORKER_REV}" \
  --force-new-deployment \
  --region "${AWS_REGION}"
