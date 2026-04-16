from fastapi.testclient import TestClient

from app.api.main import app


def test_index_serves_overview_ui() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Docling System" in response.text
    assert (
        "Observe the corpus, verify every change, and promote only what is earned."
        in response.text
    )
    assert "System diagram" in response.text
    assert "Validation-gated promotion" in response.text
    assert "Governed retrieval" in response.text
    assert "Agent orchestration" in response.text
    assert "/ui/search.html" in response.text
    assert "/ui/evals.html" in response.text
    assert "/ui/agents.html" in response.text
    assert "/ui/app.js" in response.text


def test_search_page_serves_dedicated_search_workspace() -> None:
    client = TestClient(app)

    response = client.get("/ui/search.html")

    assert response.status_code == 200
    assert "Search workspace" in response.text
    assert (
        "Query the active corpus, compare harnesses, and inspect ranked evidence directly."
        in response.text
    )
    assert "Harness registry" in response.text
    assert "Search discipline" in response.text
    assert "Run search" in response.text


def test_eval_and_agent_pages_expose_governance_workflows() -> None:
    client = TestClient(app)

    eval_response = client.get("/ui/evals.html")
    agent_response = client.get("/ui/agents.html")

    assert eval_response.status_code == 200
    assert "Eval and verification" in eval_response.text
    assert "Harness evaluation" in eval_response.text
    assert "Compare baseline and candidate retrieval behavior" in eval_response.text
    assert "Mined gaps and likely fixture additions" in eval_response.text

    assert agent_response.status_code == 200
    assert "Agent workflows" in agent_response.text
    assert (
        "Bounded agents evaluate the system, draft retrieval changes, and stop at governance gates."
        in agent_response.text
    )
    assert "Why agents draft harnesses" in agent_response.text
    assert "What each harness is for" in agent_response.text
