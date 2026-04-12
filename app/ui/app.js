const state = {
  currentDocumentId: null,
  pollTimer: null,
};

const healthPill = document.getElementById("health-pill");
const documentPill = document.getElementById("document-pill");
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
const searchForm = document.getElementById("search-form");
const searchResults = document.getElementById("search-results");

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("Health check failed");
    healthPill.textContent = "Ready";
    healthPill.className = "metric-value ok";
  } catch (error) {
    healthPill.textContent = "Offline";
    healthPill.className = "metric-value error";
  }
}

function renderDocuments(documents) {
  if (!documents.length) {
    documentsList.className = "documents-list empty";
    documentsList.textContent = "No documents loaded yet. Use docling-system-ingest-file locally to queue PDFs.";
    return;
  }

  documentsList.className = "documents-list";
  documentsList.innerHTML = documents
    .map(
      (document) => `
        <button class="document-card ${document.document_id === state.currentDocumentId ? "selected" : ""}" type="button" data-document-id="${document.document_id}">
          <strong>${escapeHtml(document.title || document.source_filename)}</strong>
          <span>${escapeHtml(document.source_filename)}</span>
          <span>Latest: ${escapeHtml(document.latest_run_status || "unknown")}</span>
          <span>Validation: ${escapeHtml(document.latest_validation_status || "pending")}</span>
          <span>${document.table_count || 0} tables</span>
          <span>${document.figure_count || 0} diagrams</span>
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

function renderChunks(chunks) {
  if (!chunks.length) {
    chunksList.className = "chunks-list empty";
    chunksList.textContent = "No active chunks yet.";
    return;
  }

  chunksList.className = "chunks-list";
  chunksList.innerHTML = chunks
    .slice(0, 8)
    .map(
      (chunk) => `
        <article class="chunk-card">
          <div class="chunk-meta">
            <span>Chunk ${chunk.chunk_index}</span>
            <span>Pages ${chunk.page_from ?? "?"}-${chunk.page_to ?? "?"}</span>
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
    .slice(0, 8)
    .map(
      (table) => `
        <article class="table-card">
          <div class="table-meta">
            <span>Table ${table.table_index + 1}</span>
            <span>Pages ${table.page_from ?? "?"}-${table.page_to ?? "?"}</span>
            <span>${table.row_count ?? "?"} rows x ${table.col_count ?? "?"} cols</span>
          </div>
          ${table.title ? `<strong>${escapeHtml(table.title)}</strong>` : ""}
          ${table.heading ? `<p class="table-heading">${escapeHtml(table.heading)}</p>` : ""}
          <p>${escapeHtml(table.preview_text)}</p>
          <div class="artifact-links table-links">
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
    .slice(0, 8)
    .map(
      (figure) => `
        <article class="table-card">
          <div class="table-meta">
            <span>Figure ${figure.figure_index + 1}</span>
            <span>Pages ${figure.page_from ?? "?"}-${figure.page_to ?? "?"}</span>
            <span>Confidence ${figure.confidence != null ? Number(figure.confidence).toFixed(2) : "n/a"}</span>
          </div>
          ${figure.caption ? `<strong>${escapeHtml(figure.caption)}</strong>` : "<strong>Uncaptioned figure</strong>"}
          ${figure.heading ? `<p class="table-heading">${escapeHtml(figure.heading)}</p>` : ""}
          <div class="artifact-links table-links">
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
    setFeedback(evaluationFeedback, "No persisted evaluation exists for the latest run.");
    evaluationQueries.className = "tables-list empty";
    evaluationQueries.textContent = "No evaluation results yet.";
    return;
  }

  evaluationStatusEl.textContent = evaluation.status;
  evaluationSummaryPillEl.textContent = `${evaluation.passed_queries}/${evaluation.query_count} passed`;
  const structuralFailures = evaluation.summary?.failed_structural_checks ?? 0;
  const summaryNote =
    evaluation.status === "completed"
      ? `${evaluation.failed_queries} failed, ${evaluation.regressed_queries} regressed, ${evaluation.improved_queries} improved, ${structuralFailures} structural failed.`
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
    .slice(0, 8)
    .map(
      (row) => `
        <article class="table-card">
          <div class="table-meta">
            <span>${escapeHtml(row.mode)}</span>
            <span>${row.passed ? "pass" : "fail"}</span>
            <span>candidate rank ${row.candidate_rank ?? "n/a"}</span>
            <span>baseline rank ${row.baseline_rank ?? "n/a"}</span>
            <span>delta ${row.rank_delta ?? "n/a"}</span>
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
              <span>Pages ${result.page_from ?? "?"}-${result.page_to ?? "?"}</span>
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
            <span>Pages ${result.page_from ?? "?"}-${result.page_to ?? "?"}</span>
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
        <span>${payload.used_fallback ? "extractive fallback" : "model answer"}</span>
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
  const documents = await fetchDocuments();
  if (!state.currentDocumentId && documents.length) {
    state.currentDocumentId = documents[0].document_id;
  }
  renderDocuments(documents);
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
    documentPill.className = "metric-value subtle";
    activeRunStatusEl.textContent = document.active_run_status || "Not active";
    latestRunStatusEl.textContent = document.latest_run_status || "Unknown";
    validationStatusEl.textContent = document.latest_validation_status || "Pending";
    promotionStatusEl.textContent = document.latest_run_promoted ? "Promoted" : "Not promoted";
    setArtifactLink(jsonLink, `/documents/${document.document_id}/artifacts/json`, document.has_json_artifact);
    setArtifactLink(yamlLink, `/documents/${document.document_id}/artifacts/yaml`, document.has_yaml_artifact);

    const note = document.is_searchable
      ? `Document is searchable with ${document.table_count ?? 0} active tables and ${document.figure_count ?? 0} active diagrams.`
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

  chatResponse.className = "chat-response empty";
  chatResponse.textContent = "Retrieving evidence and drafting an answer...";
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
  } catch (error) {
    renderChatResponse(null);
    chatResponse.className = "chat-response empty";
    chatResponse.textContent = error.message || "Chat request failed.";
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
  } catch (error) {
    searchResults.className = "search-results empty";
    searchResults.textContent = error.message || "Search failed.";
  }
});

checkHealth();
setArtifactLink(jsonLink, "#", false);
setArtifactLink(yamlLink, "#", false);
syncChatScopeState();
renderChatResponse(null);
refreshDocuments().then(refreshCurrentDocument);
startPolling();
