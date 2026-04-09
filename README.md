# docling-system

PDF ingestion and retrieval workspace built around Docling.

## Concise Note

This system turns PDFs into structured, searchable knowledge. It ingests source files, runs Docling to produce canonical parse artifacts, stores normalized chunks and metadata, generates embeddings, and exposes keyword, semantic, and hybrid retrieval through a simple API.

## System Plan

The current plan for the system is:

1. Build a Python API and ingestion worker around Docling.
2. Accept PDF uploads or trusted local file paths.
3. Store original PDFs plus derived JSON and Markdown artifacts on the local filesystem.
4. Persist document records, chunks, metadata, and embeddings in Postgres with pgvector.
5. Expose document status, chunk inspection, and search endpoints over REST.
6. Support keyword, semantic, and hybrid retrieval across normalized chunks.
7. Add retries, reprocessing, duplicate handling, and stronger observability after the core ingestion path is stable.
8. Optionally add a lightweight UI and swap local storage for S3-compatible storage in a later phase.

Detailed planning and architecture notes live in [SYSTEM_PLAN.md](./SYSTEM_PLAN.md).

## Local Run

1. Copy `.env.example` to `.env` and set `DOCLING_SYSTEM_OPENAI_API_KEY`.
2. Start Postgres with `docker compose up -d db`.
3. Install dependencies with `uv sync --extra dev`.
4. Run migrations with `uv run alembic upgrade head`.
5. Start the API with `uv run docling-system-api`.
6. Start the worker in a second shell with `uv run docling-system-worker`.

Useful commands:

- `uv run pytest tests/unit`
- `uv run docling-system-cleanup`
- `uv run alembic upgrade head --sql`
