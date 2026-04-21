from fastapi.testclient import TestClient

from app.api.main import app


def test_index_serves_overview_ui() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Docling System" in response.text
    assert (
        "Observe the corpus, verify every change, and promote only what is earned." in response.text
    )
    assert "System diagram" in response.text
    assert "Search, replay, and feedback" in response.text
    assert "Validation-gated promotion" in response.text
    assert "Governed retrieval" in response.text
    assert "Agent orchestration" in response.text
    assert "UI credential and runtime posture" in response.text
    assert "Latest eval coverage" in response.text
    assert "/ui/documents.html" in response.text
    assert "/ui/search.html" in response.text
    assert "/ui/evals.html" in response.text
    assert "/ui/semantics.html" in response.text
    assert "/ui/agents.html" in response.text
    assert "/ui/app.js" in response.text


def test_documents_page_serves_document_operator_workspace() -> None:
    client = TestClient(app)

    response = client.get("/ui/documents.html")

    assert response.status_code == 200
    assert "Document inspection" in response.text
    assert "Inspect documents, runs, artifacts, evaluations, tables, and figures." in response.text
    assert "Saved credential for current API calls" in response.text
    assert "Corpus documents" in response.text
    assert "Showing the current document browser slice." in response.text
    assert "Choose a document" in response.text
    assert "Readable system actions" in response.text
    assert "Overview" in response.text
    assert "Run log" in response.text
    assert "Artifacts" in response.text
    assert "Active outputs" in response.text
    assert "Persisted quality evidence for the active run" in response.text
    assert "Current figure inspection surface" in response.text


def test_search_page_serves_dedicated_search_workspace() -> None:
    client = TestClient(app)

    response = client.get("/ui/search.html")

    assert response.status_code == 200
    assert "Search workspace" in response.text
    assert (
        "Query the active corpus, compare harnesses, and inspect ranked evidence directly."
        in response.text
    )
    assert "Saved credential for current API calls" in response.text
    assert "Harness registry" in response.text
    assert "Search discipline" in response.text
    assert "Run search" in response.text
    assert "Readable harness roles" in response.text
    assert "Request record" in response.text
    assert "Replay lab" in response.text
    assert 'data-ui-action="replay-selected-request"' in response.text
    assert "Replay suites" in response.text
    assert "Inspect one persisted replay run" in response.text


def test_eval_and_agent_pages_expose_governance_workflows() -> None:
    client = TestClient(app)

    eval_response = client.get("/ui/evals.html")
    agent_response = client.get("/ui/agents.html")

    assert eval_response.status_code == 200
    assert "Eval and verification" in eval_response.text
    assert "Saved credential for current API calls" in eval_response.text
    assert "Harness evaluation" in eval_response.text
    assert "Compare baseline and candidate retrieval behavior" in eval_response.text
    assert "Recent harness evaluations" in eval_response.text
    assert "Mined gaps and likely fixture additions" in eval_response.text
    assert "Quality posture at a glance" in eval_response.text
    assert "Readable system actions" in eval_response.text

    assert agent_response.status_code == 200
    assert "Agent workflows" in agent_response.text
    assert "Saved credential for current API calls" in agent_response.text
    assert (
        "Bounded agents evaluate the system, draft retrieval changes, and stop at governance gates."
        in agent_response.text
    )
    assert "Inspect a durable task record" in agent_response.text
    assert "Summary, lineage, context, and artifacts" in agent_response.text
    assert "What each harness is for" in agent_response.text
    assert "Readable system actions" in agent_response.text
    assert "Report harness" in agent_response.text
    assert "Registered vertical workflow" in agent_response.text
    assert "LLM adapter and wake context" in agent_response.text
    assert "Verification and review" in agent_response.text


def test_semantics_page_exposes_backfill_observability() -> None:
    client = TestClient(app)

    response = client.get("/ui/semantics.html")

    assert response.status_code == 200
    assert "Knowledge graph migration" in response.text
    assert "Backfill active runs into governed semantic memory" in response.text
    assert "Semantic pass coverage" in response.text
    assert "Current graph-readiness state" in response.text
    assert "Run a bounded vertical slice" in response.text
    assert "Sample active documents still missing current semantic passes" in response.text
    assert 'id="page-activity-feed"' in response.text


def test_eval_ui_exposes_durable_harness_evaluation_history_actions() -> None:
    client = TestClient(app)

    response = client.get("/ui/app.js")

    assert response.status_code == 200
    assert "/search/harness-evaluations?limit=8" in response.text
    assert 'data-ui-action="load-harness-evaluation"' in response.text
    assert "loadHarnessEvaluationDetail" in response.text


def test_agent_ui_exposes_technical_report_harness_observability() -> None:
    client = TestClient(app)

    response = client.get("/ui/app.js")

    assert response.status_code == 200
    assert "TECHNICAL_REPORT_TASK_TYPES" in response.text
    assert "/agent-tasks/actions" in response.text
    assert "/agent-tasks/analytics/workflow-versions" in response.text
    assert "renderReportHarnessPacket" in response.text
    assert "missing_wake_context_count" in response.text
    assert "unresolved_evidence_card_ref_count" in response.text


def test_semantics_ui_wires_backfill_status_and_slice_actions() -> None:
    client = TestClient(app)

    response = client.get("/ui/app.js")

    assert response.status_code == 200
    assert "/semantics/backfill/status" in response.text
    assert "/semantics/backfill" in response.text
    assert "renderSemanticBackfillStatus" in response.text
    assert "loadSemanticsPage" in response.text
