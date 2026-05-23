#!/usr/bin/env bash
# Deploy backend + worker images to prod ECS (mirrors .github/workflows/deploy.yml image steps).
# Usage: ./backend/scripts/prod_deploy_backend_worker.sh [GIT_SHA]
# Requires: aws CLI, docker, jq; AWS credentials with ECR push + ECS register/update.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

AWS_REGION="${AWS_REGION:-eu-west-1}"
ECS_CLUSTER="${ECS_CLUSTER:-vector-prod}"
ECS_SERVICE="${ECS_SERVICE:-vector-backend-service}"
ECS_WORKER_SERVICE="${ECS_WORKER_SERVICE:-vector-worker-service}"
ECS_TASK_DEFINITION="${ECS_TASK_DEFINITION:-vector-backend}"
ECS_WORKER_TASK_DEFINITION="${ECS_WORKER_TASK_DEFINITION:-vector-backend-worker}"
ECR_REPOSITORY="${ECR_REPOSITORY:-vector-backend}"
WORKER_REPOSITORY="${WORKER_REPOSITORY:-vector-worker}"

IMAGE_TAG="${1:-$(git rev-parse HEAD)}"
echo "Deploying git SHA: $IMAGE_TAG"

ECR_REGISTRY="$(aws sts get-caller-identity --query Account --output text).dkr.ecr.${AWS_REGION}.amazonaws.com"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "==> Pre-deploy tests (P0-A + Phase A1)"
cd backend
python -m pip install --quiet -r requirements.txt jsonschema
export VECTOR_SETTINGS_SKIP_DOTENV=1
PYTHONPATH=src python -m pytest -q tests/vector/domains/cortex/traversal/test_walk_policy_packaging.py
PYTHONPATH=src python -m pytest -q \
  tests/vector/domains/cortex/synthesis/test_phase_a1_synthesis_job_lifecycle.py \
  tests/vector/domains/cortex/substrate_pipeline/test_continuity_p0_synthesis_job_lifecycle.py \
  tests/vector/domains/cortex/substrate_pipeline/test_continuity_p0_ecs_deploy_align.py
cd "$ROOT"

echo "==> Build & push API image"
docker build -t "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" -f backend/Dockerfile backend
docker push "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"

echo "==> Build & push worker image"
docker build -t "$ECR_REGISTRY/$WORKER_REPOSITORY:$IMAGE_TAG" -f backend/worker.Dockerfile backend
docker push "$ECR_REGISTRY/$WORKER_REPOSITORY:$IMAGE_TAG"

register_and_deploy() {
  local task_family="$1"
  local ecr_repo="$2"
  local ecs_service="$3"
  local out_prefix="$4"
  local image="$ECR_REGISTRY/$ecr_repo:$IMAGE_TAG"

  aws ecs describe-task-definition \
    --task-definition "$task_family" \
    --region "$AWS_REGION" \
    --query taskDefinition > "${out_prefix}-task-def.json"

  jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)' \
    "${out_prefix}-task-def.json" > "${out_prefix}-clean.json"

  jq --arg IMAGE "$image" '.containerDefinitions[0].image = $IMAGE' \
    "${out_prefix}-clean.json" > "${out_prefix}-new.json"

  local arn
  arn="$(aws ecs register-task-definition \
    --cli-input-json "file://${out_prefix}-new.json" \
    --region "$AWS_REGION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)"

  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ecs_service" \
    --task-definition "$arn" \
    --force-new-deployment \
    --region "$AWS_REGION" \
    --output text >/dev/null

  echo "${ecs_service} -> $arn ($image)"
}

register_and_deploy "$ECS_TASK_DEFINITION" "$ECR_REPOSITORY" "$ECS_SERVICE" "api"
register_and_deploy "$ECS_WORKER_TASK_DEFINITION" "$WORKER_REPOSITORY" "$ECS_WORKER_SERVICE" "worker"

echo "==> Waiting for ECS rollouts (up to 10m)"
aws ecs wait services-stable \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" "$ECS_WORKER_SERVICE" \
  --region "$AWS_REGION"

echo "==> Verify ECS image tags"
cd backend
PYTHONPATH=src python -c "
from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import probe_prod_ecs_deploy_v1
import json, sys
d = probe_prod_ecs_deploy_v1(expected_sha='$IMAGE_TAG')
print(json.dumps(d['verification'], indent=2))
sys.exit(0 if d['verification']['deploy_matches_closure_sha'] else 1)
"
cd "$ROOT"

echo "Deploy complete: $IMAGE_TAG"
