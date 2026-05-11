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
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
