# Project Scope

This repository implements the Docling PDF ingestion and retrieval system described in `SYSTEM_PLAN.md` and the rebuilt v1 plan.

Scope for this project:

- build the full local app in this repository
- use the recommended implementation choices by default when questions arise
- continue implementation through completion rather than stopping at intermediate scaffolding
- verify behavior at each milestone before committing
- keep the system aligned to the v1 goals: upload-only ingest, durable DB-backed runs, versioned active-run promotion, OpenAI-backed embeddings, REST API, Dockerized local development, and tests

# Default Decisions

Unless the user says otherwise, prefer:

- FastAPI for the API
- SQLAlchemy plus Alembic for persistence and migrations
- psycopg with Postgres plus pgvector
- Docker Compose for local infrastructure
- one polling worker process with concurrency-safe DB leasing
- local filesystem storage rooted in this repository's `storage/` directory
- direct artifact download endpoints instead of exposing raw filesystem paths
- OpenAI as the provider, with `text-embedding-3-small` for the pinned 1536-dimension embedding contract

# Working Rules

- implement milestone by milestone
- run verification at each milestone
- commit milestone changes as you go
- avoid scope drift beyond the v1 system plan unless required to make the system buildable and testable
