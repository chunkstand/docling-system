const state = {
  currentDocumentId: null,
  pollTimer: null,
  processTimer: null,
  activeProcessKind: null,
  activeProcessStep: -1,
};

const PROCESS_PRESETS = {
  chat: [
    {
      title: "Scope question",
      detail: "Resolve selected document or whole-corpus scope and normalize the query.",
    },
    {
      title: "Retrieve evidence",
      detail: "Search active chunks and logical tables from the validated corpus.",
    },
    {
      title: "Ground answer",
      detail: "Assemble citations and synthesize only from retrieved evidence.",
    },
    {
      title: "Verification pass",
      detail: "Return cited output and expose the supporting passages for inspection.",
    },
  ],
  search: [
    {
      title: "Parse retrieval request",
      detail: "Normalize the query and resolve direct corpus filters.",
    },
    {
      title: "Search active corpus",
      detail: "Run mixed retrieval over active chunks and tables.",
    },
    {
      title: "Merge and rank",
      detail: "Combine retrieval candidates and compute the final ordering.",
    },
    {
      title: "Publish results",
      detail: "Render the scored evidence surface for operator review.",
    },
  ],
};

const healthPill = document.getElementById("health-pill");
const documentPill = document.getElementById("document-pill");
const ingestionStatusValue = document.getElementById("ingestion-status-value");
const docCountValue = document.getElementById("doc-count-value");
const verifiedCountValue = document.getElementById("verified-count-value");
const evaluatedCountValue = document.getElementById("evaluated-count-value");
const tableHitRateValue = document.getElementById("table-hit-rate-value");
const telemetryStrip = document.getElementById("telemetry-strip");
const ingestionRunLane = document.getElementById("ingestion-run-lane");
const documentsList = document.getElementById("documents-list");
const statusFeedback = document.getElementById("status-feedback");
const documentIdEl = document.getElementById("document-id");
const activeRunStatusEl = document.getElementById("active-run-status");
const latestRunStatusEl = document.getElementById("latest-run-status");
const validationStatusEl = document.getElementById("validation-status");
const promotionStatusEl = document.getElementById("promotion-status");
const evaluationStatusEl = document.getElementById("evaluation-status");
const evaluationSummaryPillEl = document.getElementById("evaluation-summary-pill");
const jsonLink = document.getElementById("json-link");
const yamlLink = document.getElementById("yaml-link");
const refreshButton = document.getElementById("refresh-button");
const reprocessButton = document.getElementById("reprocess-button");
const chunksList = document.getElementById("chunks-list");
const tablesList = document.getElementById("tables-list");
const figuresList = document.getElementById("figures-list");
const evaluationFeedback = document.getElementById("evaluation-feedback");
const evaluationQueries = document.getElementById("evaluation-queries");
const chatForm = document.getElementById("chat-form");
const chatQuestion = document.getElementById("chat-question");
const chatMode = document.getElementById("chat-mode");
const chatScope = document.getElementById("chat-scope");
const chatScopeNote = document.getElementById("chat-scope-note");
const chatWarning = document.getElementById("chat-warning");
const chatResponse = document.getElementById("chat-response");
const chatCitations = document.getElementById("chat-citations");
const searchProcess = document.getElementById("search-process");
const searchProcessCaption = document.getElementById("search-process-caption");
const searchForm = document.getElementById("search-form");
const searchResults = document.getElementById("search-results");

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatInteger(value) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value ?? 0);
}

function formatPercent(value) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function setArtifactLink(link, href, enabled) {
  link.href = href || "#";
  link.classList.toggle("disabled", !enabled);
}

function setFeedback(element, message, tone = "muted") {
  element.textContent = message;
  element.className = `feedback ${tone}`;
}

function formatPages(pageFrom, pageTo) {
  if (pageFrom == null && pageTo == null) {
    return "unknown pages";
  }
  if (pageFrom == null || pageFrom === pageTo || pageTo == null) {
    return `page ${pageFrom ?? pageTo}`;
  }
  return `pages ${pageFrom}-${pageTo}`;
}

function ingestionRuns(documents) {
  return documents.filter((document) =>
    ["queued", "processing", "validating", "retry_wait"].includes(document.latest_run_status),
  );
}

function resetProcessRail() {
  window.clearInterval(state.processTimer);
  state.processTimer = null;
  state.activeProcessKind = null;
  state.activeProcessStep = -1;
  renderProcessRail("chat", -1, "idle");
}

function renderProcessRail(kind, activeStep, status, caption = null) {
  const steps = PROCESS_PRESETS[kind];
  const idleCaption =
    kind === "search"
      ? "Waiting for a direct search request. The rail will show retrieval stages here."
      : "Waiting for a query. The rail will animate through retrieval and verification stages.";

  searchProcessCaption.textContent = caption || idleCaption;
  searchProcess.innerHTML = steps
    .map((step, index) => {
      const isComplete = status === "complete" || index < activeStep;
      const isActive = status === "running" && index === activeStep;
      const isError = status === "error" && index === activeStep;
      const className = [
        "process-step",
        isComplete ? "is-complete" : "",
        isActive ? "is-active" : "",
        isError ? "is-error" : "",
      ]
        .filter(Boolean)
        .join(" ");
      return `
        <article class="${className}">
          <div class="process-step-dot"></div>
          <div>
            <strong>${escapeHtml(step.title)}</strong>
            <span>${escapeHtml(step.detail)}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function startProcessRail(kind) {
  window.clearInterval(state.processTimer);
  state.activeProcessKind = kind;
  state.activeProcessStep = 0;
  renderProcessRail(
    kind,
    0,
    "running",
    kind === "search"
      ? "Search request received. Running mixed retrieval over the active corpus."
      : "Grounded question received. Resolving evidence against the active corpus.",
  );

  const steps = PROCESS_PRESETS[kind];
  state.processTimer = window.setInterval(() => {
    state.activeProcessStep = Math.min(state.activeProcessStep + 1, steps.length - 1);
    renderProcessRail(kind, state.activeProcessStep, "running");
  }, 650);
}

function finishProcessRail(kind, succeeded, caption) {
  window.clearInterval(state.processTimer);
  state.processTimer = null;
  const finalStep = PROCESS_PRESETS[kind].length - 1;
  state.activeProcessKind = kind;
  state.activeProcessStep = finalStep;
  renderProcessRail(kind, finalStep, succeeded ? "complete" : "error", caption);
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("Health check failed");
    healthPill.textContent = "Ready";
    healthPill.className = "signal-value ok";
  } catch (error) {
    healthPill.textContent = "Offline";
    healthPill.className = "signal-value error";
  }
}

function renderDocuments(documents) {
  if (!documents.length) {
    documentsList.className = "documents-list empty";
    documentsList.textContent =
      "No documents loaded yet. Use docling-system-ingest-file locally to queue PDFs.";
    return;
  }

  documentsList.className = "documents-list";
  documentsList.innerHTML = documents
    .map(
      (document) => `
        <button
          class="document-card ${document.document_id === state.currentDocumentId ? "selected" : ""}"
          type="button"
          data-document-id="${document.document_id}"
        >
          <strong>${escapeHtml(document.title || document.source_filename)}</strong>
          <span>${escapeHtml(document.source_filename)}</span>
          <span>run ${escapeHtml(document.latest_run_status || "unknown")} / validation ${escapeHtml(document.latest_validation_status || "pending")}</span>
          <span>${document.table_count || 0} tables · ${document.figure_count || 0} figures</span>
        </button>
      `,
    )
    .join("");

  documentsList.querySelectorAll("[data-document-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentDocumentId = button.dataset.documentId;
      renderDocuments(documents);
      refreshCurrentDocument();
    });
  });
}

function renderOverview(documents, metrics) {
  const validated = documents.filter((document) => document.latest_validation_status === "passed");
  const evaluated = documents.filter(
    (document) => document.latest_evaluation && document.latest_evaluation.status === "completed",
  );
  const activeIngestion = ingestionRuns(documents);

  docCountValue.textContent = formatInteger(documents.length);
  verifiedCountValue.textContent = formatInteger(validated.length);
  evaluatedCountValue.textContent = formatInteger(evaluated.length);
  tableHitRateValue.textContent = formatPercent(metrics.mixed_search_table_hit_rate);
  ingestionStatusValue.textContent = activeIngestion.length
    ? `${activeIngestion.length} live run${activeIngestion.length > 1 ? "s" : ""}`
    : "Idle";
}

function renderIngestionLane(documents) {
  const activeRuns = ingestionRuns(documents);
  if (!activeRuns.length) {
    ingestionRunLane.className = "ingestion-lane empty";
    ingestionRunLane.textContent = "No current ingestion run.";
    return;
  }

  ingestionRunLane.className = "ingestion-lane";
  ingestionRunLane.innerHTML = activeRuns
    .map(
      (document) => `
        <article class="ingestion-item">
          <strong>${escapeHtml(document.source_filename)}</strong>
          <span>Status: ${escapeHtml(document.latest_run_status)}</span>
          <span>Validation: ${escapeHtml(document.latest_validation_status || "pending")}</span>
        </article>
      `,
    )
    .join("");
}

function renderTelemetry(metrics) {
  telemetryStrip.className = "telemetry-strip";
  telemetryStrip.innerHTML = [
    {
      label: "Logical tables persisted",
      value: formatInteger(metrics.logical_tables_persisted_total),
      note: "Structured retrieval objects written to the corpus.",
    },
    {
      label: "Continuation merges",
      value: formatInteger(metrics.continuation_merges_total),
      note: "Merged table segments with preserved lineage.",
    },
    {
      label: "Mixed search requests",
      value: formatInteger(metrics.mixed_search_requests_total),
      note: "Requests observed through the shared retrieval path.",
    },
    {
      label: "Table search hits",
      value: formatInteger(metrics.table_search_hits_total),
      note: "Returned table evidence from active mixed retrieval.",
    },
  ]
    .map(
      (item) => `
        <article class="telemetry-item">
          <strong>${escapeHtml(item.value)} · ${escapeHtml(item.label)}</strong>
          <span>${escapeHtml(item.note)}</span>
        </article>
      `,
    )
    .join("");
}

function renderChunks(chunks) {
  if (!chunks.length) {
    chunksList.className = "chunks-list empty";
    chunksList.textContent = "No active chunks yet.";
    return;
  }

  chunksList.className = "chunks-list";
  chunksList.innerHTML = chunks
    .slice(0, 6)
    .map(
      (chunk) => `
        <article class="chunk-card">
          <div class="chunk-meta">
            <span>Chunk ${chunk.chunk_index}</span>
            <span>${escapeHtml(formatPages(chunk.page_from, chunk.page_to))}</span>
            ${chunk.heading ? `<span>${escapeHtml(chunk.heading)}</span>` : ""}
          </div>
          <p>${escapeHtml(chunk.text)}</p>
        </article>
      `,
    )
    .join("");
}

function renderTables(tables, documentId) {
  if (!tables.length) {
    tablesList.className = "tables-list empty";
    tablesList.textContent = "No active tables yet.";
    return;
  }

  tablesList.className = "tables-list";
  tablesList.innerHTML = tables
    .slice(0, 6)
    .map(
      (table) => `
        <article class="table-card">
          <div class="table-meta">
            <span>Table ${table.table_index + 1}</span>
            <span>${escapeHtml(formatPages(table.page_from, table.page_to))}</span>
            <span>${table.row_count ?? "?"} rows × ${table.col_count ?? "?"} cols</span>
          </div>
          ${table.title ? `<strong>${escapeHtml(table.title)}</strong>` : ""}
          ${table.heading ? `<p class="table-heading">${escapeHtml(table.heading)}</p>` : ""}
          <p>${escapeHtml(table.preview_text)}</p>
          <div class="artifact-links">
            <a href="/documents/${documentId}/tables/${table.table_id}/artifacts/json" target="_blank" rel="noreferrer">JSON</a>
            <a href="/documents/${documentId}/tables/${table.table_id}/artifacts/yaml" target="_blank" rel="noreferrer">YAML</a>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderFigures(figures, documentId) {
  if (!figures.length) {
    figuresList.className = "tables-list empty";
    figuresList.textContent = "No active figures yet.";
    return;
  }

  figuresList.className = "tables-list";
  figuresList.innerHTML = figures
    .slice(0, 6)
    .map(
      (figure) => `
        <article class="table-card">
          <div class="table-meta">
            <span>Figure ${figure.figure_index + 1}</span>
            <span>${escapeHtml(formatPages(figure.page_from, figure.page_to))}</span>
            <span>Confidence ${figure.confidence != null ? Number(figure.confidence).toFixed(2) : "n/a"}</span>
          </div>
          ${figure.caption ? `<strong>${escapeHtml(figure.caption)}</strong>` : "<strong>Uncaptioned figure</strong>"}
          ${figure.heading ? `<p class="table-heading">${escapeHtml(figure.heading)}</p>` : ""}
          <div class="artifact-links">
            <a href="/documents/${documentId}/figures/${figure.figure_id}/artifacts/json" target="_blank" rel="noreferrer">JSON</a>
            <a href="/documents/${documentId}/figures/${figure.figure_id}/artifacts/yaml" target="_blank" rel="noreferrer">YAML</a>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderEvaluation(evaluation) {
  if (!evaluation) {
    evaluationStatusEl.textContent = "Missing";
    evaluationSummaryPillEl.textContent = "No evaluation";
    setFeedback(
      evaluationFeedback,
      "No persisted evaluation exists for the latest run.",
    );
    evaluationQueries.className = "tables-list empty";
    evaluationQueries.textContent = "No evaluation results yet.";
    return;
  }

  evaluationStatusEl.textContent = evaluation.status;
  evaluationSummaryPillEl.textContent = `${evaluation.passed_queries}/${evaluation.query_count} passed`;
  const structuralFailures = evaluation.summary?.failed_structural_checks ?? 0;
  const summaryNote =
    evaluation.status === "completed"
      ? `${evaluation.failed_queries} failed queries, ${structuralFailures} failed structural checks, ${evaluation.improved_queries} improved results.`
      : evaluation.error_message || "Evaluation did not complete.";
  setFeedback(evaluationFeedback, summaryNote, evaluation.status === "completed" ? "muted" : "");

  const queryResults = evaluation.query_results || [];
  if (!queryResults.length) {
    evaluationQueries.className = "tables-list empty";
    evaluationQueries.textContent = "No evaluation query results yet.";
    return;
  }

  evaluationQueries.className = "tables-list";
  evaluationQueries.innerHTML = queryResults
    .slice(0, 6)
    .map(
      (row) => `
        <article class="table-card">
          <div class="table-meta">
            <span>${escapeHtml(row.mode)}</span>
            <span>${row.passed ? "pass" : "fail"}</span>
            <span>candidate rank ${row.candidate_rank ?? "n/a"}</span>
            <span>baseline rank ${row.baseline_rank ?? "n/a"}</span>
          </div>
          <strong>${escapeHtml(row.query_text)}</strong>
          <p>${escapeHtml(row.candidate_label || "No matching candidate result")}</p>
        </article>
      `,
    )
    .join("");
}

function renderSearchResults(results) {
  if (!results.length) {
    searchResults.className = "search-results empty";
    searchResults.textContent = "No results yet.";
    return;
  }

  searchResults.className = "search-results";
  searchResults.innerHTML = results
    .map((result) => {
      if (result.result_type === "table") {
        return `
          <article class="result-card">
            <div class="result-meta">
              <span>Table hit</span>
              <span>${escapeHtml(result.source_filename)}</span>
              <span>${escapeHtml(formatPages(result.page_from, result.page_to))}</span>
              <span>Score ${Number(result.score).toFixed(3)}</span>
            </div>
            ${result.table_title ? `<strong>${escapeHtml(result.table_title)}</strong>` : ""}
            ${result.table_heading ? `<p class="table-heading">${escapeHtml(result.table_heading)}</p>` : ""}
            <p>${escapeHtml(result.table_preview || "")}</p>
          </article>
        `;
      }

      return `
        <article class="result-card">
          <div class="result-meta">
            <span>Chunk hit</span>
            <span>${escapeHtml(result.source_filename)}</span>
            <span>${escapeHtml(formatPages(result.page_from, result.page_to))}</span>
            <span>Score ${Number(result.score).toFixed(3)}</span>
          </div>
          ${result.heading ? `<strong>${escapeHtml(result.heading)}</strong>` : ""}
          <p>${escapeHtml(result.chunk_text || "")}</p>
        </article>
      `;
    })
    .join("");
}

function syncChatScopeState() {
  const hasDocument = Boolean(state.currentDocumentId);
  const documentOption = chatScope.querySelector('option[value="document"]');
  documentOption.disabled = !hasDocument;
  if (!hasDocument && chatScope.value === "document") {
    chatScope.value = "corpus";
  }

  if (chatScope.value === "document" && hasDocument) {
    chatScopeNote.textContent = `Answer scope: ${documentPill.textContent || "selected document"}.`;
  } else {
    chatScopeNote.textContent = "Answer scope: whole active corpus.";
  }
}

function renderChatResponse(payload) {
  if (!payload) {
    chatResponse.className = "chat-response empty";
    chatResponse.textContent = "Answers will appear here.";
    chatCitations.className = "chat-citations empty";
    chatCitations.textContent = "Retrieved support will appear here.";
    setFeedback(chatWarning, "");
    return;
  }

  chatResponse.className = "chat-response";
  chatResponse.innerHTML = `
    <article class="answer-card">
      <div class="result-meta">
        <span>${escapeHtml(payload.mode)}</span>
        <span>${payload.used_fallback ? "extractive fallback" : "model-backed answer"}</span>
        ${payload.model ? `<span>${escapeHtml(payload.model)}</span>` : ""}
      </div>
      <p>${escapeHtml(payload.answer).replaceAll("\n", "<br />")}</p>
    </article>
  `;

  setFeedback(chatWarning, payload.warning || "");

  if (!payload.citations?.length) {
    chatCitations.className = "chat-citations empty";
    chatCitations.textContent = "No supporting passages were retrieved.";
    return;
  }

  chatCitations.className = "chat-citations";
  chatCitations.innerHTML = payload.citations
    .map(
      (citation) => `
        <article class="citation-card">
          <div class="result-meta">
            <span>[${citation.citation_index}]</span>
            <span>${escapeHtml(citation.result_type)}</span>
            <span>${escapeHtml(citation.source_filename)}</span>
            <span>${escapeHtml(formatPages(citation.page_from, citation.page_to))}</span>
            <span>Score ${Number(citation.score).toFixed(3)}</span>
          </div>
          <strong>${escapeHtml(citation.label)}</strong>
          <p>${escapeHtml(citation.excerpt)}</p>
        </article>
      `,
    )
    .join("");
}

async function fetchDocuments() {
  const response = await fetch("/documents");
  if (!response.ok) {
    throw new Error("Unable to load documents.");
  }
  return response.json();
}

async function fetchMetrics() {
  const response = await fetch("/metrics");
  if (!response.ok) {
    throw new Error("Unable to load metrics.");
  }
  return response.json();
}

async function fetchDocumentStatus(documentId) {
  const response = await fetch(`/documents/${documentId}`);
  if (!response.ok) {
    throw new Error("Unable to load document status.");
  }
  return response.json();
}

async function fetchChunks(documentId) {
  const response = await fetch(`/documents/${documentId}/chunks`);
  if (!response.ok) {
    throw new Error("Unable to load chunks.");
  }
  return response.json();
}

async function fetchTables(documentId) {
  const response = await fetch(`/documents/${documentId}/tables`);
  if (!response.ok) {
    throw new Error("Unable to load tables.");
  }
  return response.json();
}

async function fetchFigures(documentId) {
  const response = await fetch(`/documents/${documentId}/figures`);
  if (!response.ok) {
    throw new Error("Unable to load figures.");
  }
  return response.json();
}

async function fetchLatestEvaluation(documentId) {
  const response = await fetch(`/documents/${documentId}/evaluations/latest`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error("Unable to load evaluation.");
  }
  return response.json();
}

async function refreshDocuments() {
  const [documents, metrics] = await Promise.all([fetchDocuments(), fetchMetrics()]);
  if (!state.currentDocumentId && documents.length) {
    state.currentDocumentId = documents[0].document_id;
  }
  renderDocuments(documents);
  renderOverview(documents, metrics);
  renderIngestionLane(documents);
  renderTelemetry(metrics);
  syncChatScopeState();
}

async function refreshCurrentDocument() {
  if (!state.currentDocumentId) {
    setFeedback(
      statusFeedback,
      "No validated documents are loaded yet. Use docling-system-ingest-file to queue PDFs.",
    );
    renderChunks([]);
    renderTables([], "");
    renderFigures([], "");
    renderEvaluation(null);
    documentPill.textContent = "None selected";
    return;
  }

  try {
    const [document, chunks, tables, figures, evaluation] = await Promise.all([
      fetchDocumentStatus(state.currentDocumentId),
      fetchChunks(state.currentDocumentId),
      fetchTables(state.currentDocumentId),
      fetchFigures(state.currentDocumentId),
      fetchLatestEvaluation(state.currentDocumentId),
    ]);

    documentIdEl.textContent = document.document_id;
    documentPill.textContent = document.title || document.source_filename;
    documentPill.className = "signal-value subtle";
    activeRunStatusEl.textContent = document.active_run_status || "Not active";
    latestRunStatusEl.textContent = document.latest_run_status || "Unknown";
    validationStatusEl.textContent = document.latest_validation_status || "Pending";
    promotionStatusEl.textContent = document.latest_run_promoted ? "Promoted" : "Not promoted";
    setArtifactLink(
      jsonLink,
      `/documents/${document.document_id}/artifacts/json`,
      document.has_json_artifact,
    );
    setArtifactLink(
      yamlLink,
      `/documents/${document.document_id}/artifacts/yaml`,
      document.has_yaml_artifact,
    );

    const note = document.is_searchable
      ? `Document is searchable with ${document.table_count ?? 0} active tables and ${document.figure_count ?? 0} active figures.`
      : document.latest_error_message || "Latest run has not been promoted yet.";
    setFeedback(statusFeedback, note, document.is_searchable ? "muted" : "");
    renderChunks(chunks);
    renderTables(tables, document.document_id);
    renderFigures(figures, document.document_id);
    renderEvaluation(evaluation || document.latest_evaluation);
    syncChatScopeState();
  } catch (error) {
    setFeedback(statusFeedback, error.message || "Unable to refresh document state.");
  }
}

function startPolling() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
  }
  state.pollTimer = window.setInterval(async () => {
    await refreshDocuments();
    await refreshCurrentDocument();
  }, 5000);
}

refreshButton.addEventListener("click", async () => {
  await refreshDocuments();
  await refreshCurrentDocument();
});

reprocessButton.addEventListener("click", async () => {
  if (!state.currentDocumentId) {
    setFeedback(statusFeedback, "Select a document first.");
    return;
  }

  setFeedback(statusFeedback, "Queueing reprocess...");
  try {
    const response = await fetch(`/documents/${state.currentDocumentId}/reprocess`, {
      method: "POST",
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail || "Unable to reprocess.");
    }
    setFeedback(statusFeedback, `Queued run ${body.run_id}.`);
    await refreshDocuments();
    await refreshCurrentDocument();
    startPolling();
  } catch (error) {
    setFeedback(statusFeedback, error.message || "Unable to reprocess.");
  }
});

chatScope.addEventListener("change", syncChatScopeState);

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = chatQuestion.value.trim();
  const mode = chatMode.value;
  const scope = chatScope.value;

  if (!question) {
    renderChatResponse(null);
    chatResponse.className = "chat-response empty";
    chatResponse.textContent = "Enter a question before asking.";
    return;
  }

  if (scope === "document" && !state.currentDocumentId) {
    renderChatResponse(null);
    chatResponse.className = "chat-response empty";
    chatResponse.textContent = "Select a document or switch scope to the whole corpus.";
    return;
  }

  startProcessRail("chat");
  chatResponse.className = "chat-response empty";
  chatResponse.textContent = "Retrieving evidence and building a cited answer...";
  chatCitations.className = "chat-citations empty";
  chatCitations.textContent = "Waiting for supporting passages...";
  setFeedback(chatWarning, "");

  const payload = { question, mode, top_k: 6 };
  if (scope === "document" && state.currentDocumentId) {
    payload.document_id = state.currentDocumentId;
  }

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail || "Chat request failed.");
    }
    renderChatResponse(body);
    finishProcessRail(
      "chat",
      true,
      `Grounded answer completed with ${body.citations.length} supporting citation${body.citations.length === 1 ? "" : "s"}.`,
    );
    const metrics = await fetchMetrics();
    renderTelemetry(metrics);
  } catch (error) {
    renderChatResponse(null);
    chatResponse.className = "chat-response empty";
    chatResponse.textContent = error.message || "Chat request failed.";
    finishProcessRail("chat", false, error.message || "Grounded answer failed.");
  }
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = document.getElementById("search-query").value.trim();
  const mode = document.getElementById("search-mode").value;
  if (!query) {
    renderSearchResults([]);
    searchResults.className = "search-results empty";
    searchResults.textContent = "Enter a query before searching.";
    return;
  }

  startProcessRail("search");
  searchResults.className = "search-results empty";
  searchResults.textContent = "Searching...";

  const payload = { query, mode, limit: 8 };
  if (state.currentDocumentId) {
    payload.filters = { document_id: state.currentDocumentId };
  }

  try {
    const response = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail || "Search failed.");
    }
    renderSearchResults(body);
    finishProcessRail(
      "search",
      true,
      `Direct retrieval completed with ${body.length} ranked result${body.length === 1 ? "" : "s"}.`,
    );
    const metrics = await fetchMetrics();
    renderTelemetry(metrics);
  } catch (error) {
    searchResults.className = "search-results empty";
    searchResults.textContent = error.message || "Search failed.";
    finishProcessRail("search", false, error.message || "Direct search failed.");
  }
});

checkHealth();
setArtifactLink(jsonLink, "#", false);
setArtifactLink(yamlLink, "#", false);
syncChatScopeState();
renderChatResponse(null);
resetProcessRail();
refreshDocuments().then(refreshCurrentDocument);
startPolling();
