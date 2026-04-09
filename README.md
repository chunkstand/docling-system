# docling-system

PDF ingestion and retrieval workspace built around Docling.

## Concise Note

This system turns uploaded PDFs into structured, searchable knowledge. It uses Docling to produce canonical artifacts, stores versioned runs and retrieval chunks, promotes only successful runs to active status, and exposes keyword, semantic, and hybrid search through a local REST API and UI.

## System Plan

The current plan for the system is:

1. Accept multipart PDF uploads only on the public API.
2. Deduplicate documents by checksum and reuse the canonical document row.
3. Process every attempt through a durable `document_runs` queue/lease model.
4. Store source PDFs and versioned Docling artifacts on the local filesystem.
5. Persist documents, runs, chunks, and embeddings in Postgres with pgvector.
6. Promote only fully successful runs to `active_run_id` so search sees a stable version.
7. Expose document status, chunk inspection, reprocessing, artifact download, and search endpoints.
8. Keep retention, retries, and search filters intentionally small and explicit for v1.

Detailed planning and architecture notes live in [SYSTEM_PLAN.md](./SYSTEM_PLAN.md).

## Local Run

1. Copy `.env.example` to `.env` and set `DOCLING_SYSTEM_OPENAI_API_KEY`.
2. Start Postgres with `docker compose up -d db`.
3. Install dependencies with `uv sync --extra dev`.
4. Run migrations with `uv run alembic upgrade head`.
5. Start the API with `uv run docling-system-api`.
6. Start the worker in a second shell with `uv run docling-system-worker`.
7. Open `http://localhost:8000/` in your browser.

Useful commands:

- `uv run pytest tests/unit`
- `uv run docling-system-cleanup`
- `uv run alembic upgrade head --sql`
