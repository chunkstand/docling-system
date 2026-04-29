from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=16)
def _load_corpus_documents_from_stat(
    path_value: str,
    mtime_ns: int,
    size: int,
) -> tuple[dict[str, Any], ...]:
    del mtime_ns, size
    path = Path(path_value)
    config = yaml.safe_load(path.read_text()) or {}
    documents = config.get("documents") or []
    return tuple(document for document in documents if isinstance(document, dict))


def load_corpus_documents_cached(path: Path) -> list[dict[str, Any]]:
    resolved = path.expanduser().resolve()
    try:
        stat = resolved.stat()
    except FileNotFoundError:
        return []
    documents = _load_corpus_documents_from_stat(
        str(resolved),
        stat.st_mtime_ns,
        stat.st_size,
    )
    return [dict(document) for document in documents]
