from __future__ import annotations

from types import SimpleNamespace

from app.services.runtime import (
    get_runtime_status,
    register_runtime_process,
    runtime_code_is_current,
)


def test_register_runtime_process_marks_older_fingerprint_stale(monkeypatch, tmp_path) -> None:
    storage_root = tmp_path / "storage"
    current_fingerprint = {"value": "fingerprint-old"}

    monkeypatch.setattr(
        "app.services.runtime.get_settings",
        lambda: SimpleNamespace(storage_root=storage_root),
    )
    monkeypatch.setattr(
        "app.services.runtime.get_startup_code_fingerprint",
        lambda: current_fingerprint["value"],
    )

    first = register_runtime_process("agent_worker", "agent-worker-old", pid=101)
    first_status = get_runtime_status("agent-worker-old")

    assert first.startup_code_fingerprint == "fingerprint-old"
    assert first_status["desired_code_fingerprint"] == "fingerprint-old"
    assert runtime_code_is_current(first.startup_code_fingerprint) is True

    current_fingerprint["value"] = "fingerprint-new"
    second = register_runtime_process("agent_worker", "agent-worker-new", pid=202)
    old_status = get_runtime_status("agent-worker-old")
    new_status = get_runtime_status("agent-worker-new")

    assert second.startup_code_fingerprint == "fingerprint-new"
    assert old_status["registered_process"]["startup_code_fingerprint"] == "fingerprint-old"
    assert new_status["registered_process"]["startup_code_fingerprint"] == "fingerprint-new"
    assert old_status["desired_code_fingerprint"] == "fingerprint-new"
    assert new_status["desired_code_fingerprint"] == "fingerprint-new"
    assert runtime_code_is_current(first.startup_code_fingerprint) is False
    assert runtime_code_is_current(second.startup_code_fingerprint) is True
