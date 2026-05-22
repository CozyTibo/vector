FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "from jose import jwt as _jose_jwt; import bcrypt; from openai import OpenAI"

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
# Test-only / dev dataset helpers imported as top-level `mock_connectors` by pytest (see tests/conftest.py).
COPY mock_connectors ./mock_connectors

ENV PYTHONPATH=/app/src

# P0-A (CONT-INV-02): phase 05 validates SUBSTRATE_WALK_POLICY_V1 at runtime; schema is bundled under
# vector/domains/cortex/traversal/schemas/ (also copied via src/). Fail the image build if missing.
RUN python -c "from vector.domains.cortex.substrate_pipeline.substrate_traversal_execution import SUBSTRATE_WALK_POLICY_V1; from vector.domains.cortex.traversal.walk_policy import bundled_oct_walk_policy_v1_schema_path, validate_walk_policy_for_request_v1; assert bundled_oct_walk_policy_v1_schema_path().is_file(); validate_walk_policy_for_request_v1(SUBSTRATE_WALK_POLICY_V1, walk_execution_strategy='ONLINE_OBSERVED', exploration_mode=False, enforce_sync_caps=False); print('walk_policy_packaging_ok')"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
