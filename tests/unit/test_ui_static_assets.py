from fastapi.testclient import TestClient

from app.api.main import app

UI_PAGES = (
    ("/", "/ui/modules/landing.js"),
    ("/ui/documents.html", "/ui/modules/documents.js"),
    ("/ui/search.html", "/ui/modules/search.js"),
    ("/ui/evals.html", "/ui/modules/evals.js"),
    ("/ui/semantics.html", "/ui/modules/semantics.js"),
    ("/ui/agents.html", "/ui/modules/agents.js"),
)


def test_ui_entrypoints_include_shared_runtime_and_bootstrap_assets() -> None:
    client = TestClient(app)

    for page_path, page_module_path in UI_PAGES:
        response = client.get(page_path)

        assert response.status_code == 200
        assert "/ui/modules/shared_runtime.js" in response.text
        assert "/ui/modules/shared.js" in response.text
        assert "/ui/modules/shared_search_rendering.js" in response.text
        assert "/ui/modules/agents_collections.js" in response.text
        assert "/ui/modules/agents_claim_support_replay.js" in response.text
        assert "/ui/modules/agents_report_harness.js" in response.text
        assert page_module_path in response.text
        assert "/ui/app.js" in response.text


def test_ui_module_assets_are_served() -> None:
    client = TestClient(app)

    for asset_path in (
        "/ui/modules/shared_runtime.js",
        "/ui/modules/shared.js",
        "/ui/modules/shared_search_rendering.js",
        "/ui/modules/landing.js",
        "/ui/modules/documents.js",
        "/ui/modules/search.js",
        "/ui/modules/evals.js",
        "/ui/modules/semantics.js",
        "/ui/modules/agents_collections.js",
        "/ui/modules/agents_claim_support_replay.js",
        "/ui/modules/agents_report_harness.js",
        "/ui/modules/agents.js",
        "/ui/app.js",
    ):
        response = client.get(asset_path)

        assert response.status_code == 200
        assert response.text
