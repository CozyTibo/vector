# Vector backend

Python service. Run from repo root with Docker Compose — see [`../DOCS/base-app-and-repository-setup.md`](../DOCS/base-app-and-repository-setup.md).

## Celery + Redis

Compose includes **redis** and **celery-worker**. Set **`REDIS_URL`** (e.g. `redis://redis:6379/0` in Docker, `redis://127.0.0.1:6379/0` on the host).

- Worker: `celery -A app.worker worker --loglevel=info`

**Host shell (not Docker):** install backend deps into your venv so `celery` is importable, e.g. from `backend/`: `pip install -e .` Then run snippets with `PYTHONPATH=src` from the **`backend`** directory (or `PYTHONPATH=backend/src` from the repo root). If you see `ModuleNotFoundError: No module named 'celery'`, the active Python does not have the backend environment.

## Email (SMTP)

Outbound mail uses **`vector.infrastructure.email`**: build an **`EmailEnvelope`**, then **`enqueue_email()`** (Celery task `vector.email.send`) or **`send_email_sync()`** for tests. Set **`SMTP_HOST`**, **`EMAIL_FROM_ADDRESS`**, and Mailtrap or SES SMTP credentials in `.env` (see repo **`.env.example`**). The **celery-worker** must be running for queued sends.
