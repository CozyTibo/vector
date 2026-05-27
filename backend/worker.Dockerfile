FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src

ENV PYTHONPATH=/app/src

RUN python -c "from app.tasks.cortex_ingestion_sync import run_cortex_connector_sync_task; from app.tasks.cortex_ingestion_scheduler import cortex_ingestion_scheduler_tick; print('cortex_ingestion_worker_packaging_ok')"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["celery", "-A", "app.worker", "worker", "--loglevel=info"]
