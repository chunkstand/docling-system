from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.api import main


def test_run_uses_configured_bind_host_and_port(monkeypatch) -> None:
    captured: dict = {}

    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(
            api_mode="local",
            api_host="127.0.0.1",
            api_port=9001,
            api_key=None,
        ),
    )
    monkeypatch.setattr(
        "app.api.main.uvicorn.run",
        lambda target, host, port, reload: captured.update(
            {"target": target, "host": host, "port": port, "reload": reload}
        ),
    )

    main.run()

    assert captured == {
        "target": "app.api.main:app",
        "host": "127.0.0.1",
        "port": 9001,
        "reload": False,
    }


def test_run_rejects_non_loopback_bind_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(api_mode=None, api_host="0.0.0.0", api_port=8000, api_key=None),
    )

    with pytest.raises(
        ValueError,
        match=(
            "DOCLING_SYSTEM_API_KEY or DOCLING_SYSTEM_API_CREDENTIALS_JSON must be set "
            "when binding the API to a non-loopback host."
        ),
    ):
        main.run()


def test_run_rejects_local_mode_when_host_is_not_loopback(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(
            api_mode="local",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="secret",
        ),
    )

    with pytest.raises(
        ValueError,
        match="DOCLING_SYSTEM_API_MODE=local requires DOCLING_SYSTEM_API_HOST to remain loopback.",
    ):
        main.run()


def test_run_rejects_remote_mode_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="127.0.0.1",
            api_port=8000,
            api_key=None,
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "DOCLING_SYSTEM_API_MODE=remote requires DOCLING_SYSTEM_API_KEY or "
            "DOCLING_SYSTEM_API_CREDENTIALS_JSON to be set."
        ),
    ):
        main.run()


def test_run_accepts_remote_mode_with_actor_scoped_credentials(monkeypatch) -> None:
    captured: dict = {}

    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=9002,
            api_key=None,
            api_credentials_json=json.dumps(
                [
                    {
                        "actor": "operator",
                        "key": "operator-secret",
                        "capabilities": ["*"],
                    }
                ]
            ),
        ),
    )
    monkeypatch.setattr(
        "app.api.main.uvicorn.run",
        lambda target, host, port, reload: captured.update(
            {"target": target, "host": host, "port": port, "reload": reload}
        ),
    )

    main.run()

    assert captured == {
        "target": "app.api.main:app",
        "host": "0.0.0.0",
        "port": 9002,
        "reload": False,
    }


def test_run_rejects_invalid_actor_scoped_credentials_json(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=9002,
            api_key=None,
            api_credentials_json="{invalid-json",
        ),
    )

    with pytest.raises(
        ValueError,
        match="DOCLING_SYSTEM_API_CREDENTIALS_JSON must be valid JSON.",
    ):
        main.run()
