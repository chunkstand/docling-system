from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"revision_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Failed to load migration module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_alembic_revision_ids_fit_default_version_table_width() -> None:
    versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    paths = sorted(versions_dir.glob("*.py"))

    assert paths, "Expected Alembic migration files to exist."

    oversized = []
    for path in paths:
        module = _load_revision_module(path)
        revision = getattr(module, "revision", None)
        if revision is None:
            oversized.append((path.name, "missing revision identifier"))
            continue
        if len(revision) > 32:
            oversized.append((path.name, revision))

    assert oversized == [], (
        "Alembic revision ids must fit the default alembic_version.version_num "
        f"VARCHAR(32) width, found oversized entries: {oversized}"
    )
