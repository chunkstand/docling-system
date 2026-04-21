from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from app.services.telemetry import (
    flush_metrics,
    increment,
    observe_search_results,
    snapshot_metrics,
)


def test_snapshot_metrics_reports_mixed_search_table_hit_rate(monkeypatch) -> None:
    with TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(
            "app.services.telemetry.get_settings",
            lambda: SimpleNamespace(storage_root=Path(temp_dir)),
        )
        baseline = snapshot_metrics()
        increment("tables_detected_total", 2)
        observe_search_results(table_hits=3, mixed_request=True)
        metrics = snapshot_metrics()

        assert metrics["tables_detected_total"] >= baseline["tables_detected_total"] + 2
        assert metrics["table_search_hits_total"] >= baseline["table_search_hits_total"] + 3
        assert metrics["mixed_search_requests_total"] >= baseline["mixed_search_requests_total"] + 1
        assert (
            metrics["mixed_search_requests_with_table_hits_total"]
            >= baseline.get("mixed_search_requests_with_table_hits_total", 0) + 1
        )
        assert 0 < metrics["mixed_search_table_hit_rate"] <= 1


def test_snapshot_metrics_tolerates_empty_metrics_file(monkeypatch) -> None:
    with TemporaryDirectory() as temp_dir:
        storage_root = Path(temp_dir)
        monkeypatch.setattr(
            "app.services.telemetry.get_settings",
            lambda: SimpleNamespace(storage_root=storage_root),
        )
        (storage_root / "telemetry.json").write_text("")

        metrics = snapshot_metrics()

        assert metrics["tables_detected_total"] == 0
        assert metrics["mixed_search_table_hit_rate"] == 0.0


def test_increment_tolerates_empty_metrics_file(monkeypatch) -> None:
    with TemporaryDirectory() as temp_dir:
        storage_root = Path(temp_dir)
        monkeypatch.setattr(
            "app.services.telemetry.get_settings",
            lambda: SimpleNamespace(storage_root=storage_root),
        )
        metrics_path = storage_root / "telemetry.json"
        metrics_path.write_text("")

        increment("tables_detected_total", 2)
        flush_metrics()

        payload = json.loads(metrics_path.read_text())
        assert payload["tables_detected_total"] == 2
