FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra api --extra ingest --no-install-project

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY config ./config
COPY docs ./docs

RUN uv sync --frozen --no-dev --extra api --extra ingest

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1

CMD ["docling-system-api"]
