FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra api --extra ingest --no-install-project

COPY README.md ./README.md
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY config ./config
COPY docs ./docs

RUN uv sync --frozen --no-dev --extra api --extra ingest

CMD ["docling-system-api"]
