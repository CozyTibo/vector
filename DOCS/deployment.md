# Production deployment (AWS)

This monorepo is set up for **AWS ECS Fargate** (API + worker), **RDS PostgreSQL**, **ElastiCache Redis**, **S3 + CloudFront** for the Vite frontend, **ECR** for images, and **GitHub Actions** for CI/CD.

## Architecture

| Component        | AWS service        | Notes |
|-----------------|--------------------|--------|
| HTTP API        | ECS Fargate        | `backend/Dockerfile`, port **8000**, health **`GET /health`** |
| Background jobs | ECS Fargate        | `backend/worker.Dockerfile`, **Celery** worker |
| Database        | RDS PostgreSQL     | SQLAlchemy URL in **`DATABASE_URL`** |
| Broker / cache  | ElastiCache Redis  | **`REDIS_URL`** (Celery broker; API can use same for future features) |
| Static UI       | S3 + CloudFront    | `frontend` build output **`dist/`** |
| Images          | ECR                | Separate repositories for API and worker (see workflow) |

## Environment variables

Configuration is read from the process environment (and optionally a local `.env` file via Pydantic Settings). Copy **`.env.example`** at the repo root and adjust.

| Variable | Required (prod) | Purpose |
|----------|-----------------|---------|
| `DATABASE_URL` | Yes | Async/sync SQLAlchemy DSN, e.g. `postgresql+psycopg://...` |
| `REDIS_URL` | Yes (worker) | Celery broker/backend; use `rediss://` when TLS is enabled on ElastiCache |
| `SECRET_KEY` | Yes | Session/signing secret (long random string) |
| `ENV` | Recommended | e.g. `production` — logged at startup |
| `VITE_API_BASE_URL` | At build time | Public API URL baked into the frontend bundle |
| `FRONTEND_URL` | Typical | Absolute URL of the SPA (redirects, emails) |
| `CORS_ORIGINS` | Typical | Comma-separated origins allowed by the API |

Optional: `CELERY_RESULT_BACKEND` (defaults to `REDIS_URL` in `app.worker`), connector OAuth variables, `ADMIN_PASSWORD`, etc. See `.env.example`.

## Docker images

- **API** (`backend/Dockerfile`): Python **3.11**, `pip install -r requirements.txt`, **`uvicorn app.main:app --host 0.0.0.0 --port 8000`**.
- **Worker** (`backend/worker.Dockerfile`): Same base and dependencies, **`celery -A app.worker worker --loglevel=info`**.

The `app` package under `backend/src/app/` re-exports the FastAPI app and defines the Celery application so CLI module paths match the production commands.

Build context for both images is the **`backend/`** directory.

## Health checks

ECS or an ALB should use:

- **`GET /health`** → `{"status":"ok"}` (primary target health)
- **`GET /health/live`** → same payload (optional alias)

## Frontend build

From `frontend/`:

```bash
npm ci
npm run build
```

Artifacts are written to **`dist/`** (configured explicitly in `vite.config.ts`). Sync that directory to the S3 website or origin bucket; set **`VITE_API_BASE_URL`** in CI to your public API URL before building.

## GitHub Actions pipeline

Workflow: **`.github/workflows/deploy.yml`** (runs on push to **`main`**).

1. Checkout  
2. Configure AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`; region from workflow **`env.AWS_REGION`**)  
3. Log in to **ECR**  
4. Build and push **backend** image (`$ECR_REPOSITORY`, e.g. **`vector-backend`**)  
5. Build and push **worker** image (`$WORKER_REPOSITORY`, e.g. **`vector-worker`**)  
6. **Node**: `npm ci` + **`npm run build`** in `frontend/` (uses **`VITE_API_BASE_URL`**)  
7. **`aws s3 sync`** `frontend/dist` → **`S3_BUCKET_FRONTEND`**  
8. **CloudFront** invalidation **`/*`** via **`CLOUDFRONT_DISTRIBUTION_ID`**  
9. **`aws ecs update-service --force-new-deployment`** on **`ECS_CLUSTER`** / **`ECS_SERVICE`** (workflow `env`, e.g. **`vector-prod`** / **`vector-backend-service`**)

### Workflow `env` (see **`.github/workflows/deploy.yml`**)

| Variable | Example | Purpose |
|----------|---------|---------|
| `AWS_REGION` | `eu-west-1` | Region for AWS CLI and ECR |
| `ECR_REPOSITORY` | `vector-backend` | ECR repo name for API image |
| `WORKER_REPOSITORY` | `vector-worker` | ECR repo name for worker image |
| `ECS_CLUSTER` | `vector-prod` | ECS cluster for API redeploy |
| `ECS_SERVICE` | `vector-backend-service` | ECS service for API |

### GitHub secrets checklist

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | IAM user or role key (prefer OIDC + role in hardened setups) |
| `AWS_SECRET_ACCESS_KEY` | Paired secret |
| `VITE_API_BASE_URL` | Public API base URL for the SPA build |
| `S3_BUCKET_FRONTEND` | Bucket name for static assets |
| `CLOUDFRONT_DISTRIBUTION_ID` | Distribution to invalidate |

Add a second **`aws ecs update-service`** step for the **worker** service when you want CI to roll it, using another workflow `env` key such as `ECS_SERVICE_WORKER`.

## AWS infrastructure (outline)

1. **VPC** with private subnets for ECS tasks, RDS, and ElastiCache; public subnets for ALB if used.  
2. **RDS PostgreSQL**: create database and user; set **`DATABASE_URL`** on the API task.  
3. **ElastiCache Redis**: enable TLS if required; set **`REDIS_URL`** on worker (and API if needed).  
4. **ECR**: two repositories; task definitions reference `:latest` or immutable tags (e.g. Git SHA).  
5. **ECS**: Fargate services for API (port 8000, health check HTTP **`/health`**) and worker (no inbound port).  
6. **S3** bucket for `dist/` assets; **CloudFront** with OAI/OAC; SPA error pages routed to `index.html` if using client-side routing.  
7. **Security groups**: ALB → API task 8000; API/worker → RDS 5432 and Redis 6379; no public access to RDS/Redis.

## Local parity

**`docker-compose.yml`** runs the API with **`uvicorn app.main:app`** against local Postgres. For full local parity with Redis/Celery, add a Redis service and run the worker with the same `REDIS_URL`.

## Root `.dockerignore`

The repo root **`.dockerignore`** keeps `node_modules`, `dist`, `.git`, `.env`, and Python caches out of arbitrary `docker build` contexts. Backend-specific ignores remain in **`backend/.dockerignore`**.
