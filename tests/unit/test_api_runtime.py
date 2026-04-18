from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api import main


def test_run_uses_configured_bind_host_and_port(monkeypatch) -> None:
    captured: dict = {}

    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(api_host="127.0.0.1", api_port=9001, api_key=None),
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
        lambda: SimpleNamespace(api_host="0.0.0.0", api_port=8000, api_key=None),
    )

    with pytest.raises(
        ValueError,
        match="DOCLING_SYSTEM_API_KEY must be set when binding the API to a non-loopback host.",
    ):
        main.run()
