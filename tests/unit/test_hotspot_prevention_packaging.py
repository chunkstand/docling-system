from __future__ import annotations

import tomllib
from pathlib import Path


def test_pyproject_exposes_hotspot_prevention_entrypoint() -> None:
    scripts = tomllib.loads(Path("pyproject.toml").read_text())["project"]["scripts"]

    assert scripts["docling-system-hotspot-prevention-check"] == "app.hotspot_prevention:run"
