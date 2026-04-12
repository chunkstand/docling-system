const state = {
  currentDocumentId: null,
  selectionCleared: false,
  pollTimer: null,
  processTimer: null,
  activeProcessKind: null,
  activeProcessStep: -1,
  lastSearchRequestId: null,
  lastChatAnswerId: null,
  harnesses: [],
  selectedReplayRunId: null,
  replayRuns: [],
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
const clearSelectionButton = document.getElementById("clear-selection-button");
const reprocessButton = document.getElementById("reprocess-button");
const chunksList = document.getElementById("chunks-list");
const tablesList = document.getElementById("tables-list");
const figuresList = document.getElementById("figures-list");
const evaluationFeedback = document.getElementById("evaluation-feedback");
const evaluationQueries = document.getElementById("evaluation-queries");
const runsList = document.getElementById("runs-list");
const qualityEvalCoverageValue = document.getElementById("quality-eval-coverage");
const qualityFailedQueryCountValue = document.getElementById("quality-failed-query-count");
const qualityStructuralFailureCountValue = document.getElementById(
  "quality-structural-failure-count",
);
const qualityFailedRunCountValue = document.getElementById("quality-failed-run-count");
const qualityFeedback = document.getElementById("quality-feedback");
const qualityEvaluations = document.getElementById("quality-evaluations");
const qualityFailureStages = document.getElementById("quality-failure-stages");
const qualityFailures = document.getElementById("quality-failures");
const qualityEvalCandidates = document.getElementById("quality-eval-candidates");
const qualityTrends = document.getElementById("quality-trends");
const replayRunForm = document.getElementById("replay-run-form");
const replaySourceType = document.getElementById("replay-source-type");
const replayLimit = document.getElementById("replay-limit");
const replayHarness = document.getElementById("replay-harness");
const searchReplays = document.getElementById("search-replays");
const replayCompareForm = document.getElementById("replay-compare-form");
const replayBaseline = document.getElementById("replay-baseline");
const replayCandidate = document.getElementById("replay-candidate");
const replayFeedback = document.getElementById("replay-feedback");
const replayComparison = document.getElementById("replay-comparison");
const replayDetail = document.getElementById("replay-detail");
const chatForm = document.getElementById("chat-form");
const chatQuestion = document.getElementById("chat-question");
const chatMode = document.getElementById("chat-mode");
const chatHarness = document.getElementById("chat-harness");
const chatScope = document.getElementById("chat-scope");
const chatScopeNote = document.getElementById("chat-scope-note");
const chatWarning = document.getElementById("chat-warning");
const chatResponse = document.getElementById("chat-response");
const chatFeedback = document.getElementById("chat-feedback");
const chatFeedbackActions = document.getElementById("chat-feedback-actions");
const chatCitations = document.getElementById("chat-citations");
const searchProcess = document.getElementById("search-process");
const searchProcessCaption = document.getElementById("search-process-caption");
const searchForm = document.getElementById("search-form");
const searchHarness = document.getElementById("search-harness");
const searchFeedback = document.getElementById("search-feedback");
const searchFeedbackActions = document.getElementById("search-feedback-actions");
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

function formatTimestamp(value) {
  if (!value) {
    return "pending";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function setSelectOptions(select, rows, fallbackLabel) {
  if (!rows.length) {
    select.innerHTML = `<option value="">${escapeHtml(fallbackLabel)}</option>`;
    select.disabled = true;
    return;
  }

  select.disabled = false;
  const currentValue = select.value;
  select.innerHTML = rows
    .map(
      (row) => `
        <option value="${escapeHtml(row.harness_name)}">
          ${escapeHtml(row.harness_name)} · ${escapeHtml(row.reranker_version)} · ${escapeHtml(row.retrieval_profile_name)}
        </option>
      `,
    )
    .join("");
  const defaultValue =
    rows.find((row) => row.is_default)?.harness_name || rows[0]?.harness_name || "";
  select.value = rows.some((row) => row.harness_name === currentValue) ? currentValue : defaultValue;
}

function renderHarnessSelects(rows) {
  state.harnesses = rows;
  setSelectOptions(searchHarness, rows, "No harnesses available");
  setSelectOptions(chatHarness, rows, "No harnesses available");
  setSelectOptions(replayHarness, rows, "No harnesses available");
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
      state.selectionCleared = false;
      renderDocuments(documents);
      refreshCurrentDocument();
    });
  });
}

function resetDocumentSelectionState() {
  documentIdEl.textContent = "No document selected";
  documentPill.textContent = "None selected";
  documentPill.className = "signal-value subtle";
  activeRunStatusEl.textContent = "Unknown";
  latestRunStatusEl.textContent = "Unknown";
  validationStatusEl.textContent = "Unknown";
  promotionStatusEl.textContent = "Unknown";
  evaluationStatusEl.textContent = "Missing";
  evaluationSummaryPillEl.textContent = "No evaluation";
  setArtifactLink(jsonLink, "#", false);
  setArtifactLink(yamlLink, "#", false);
  renderChunks([]);
  renderTables([], "");
  renderFigures([], "");
  renderEvaluation(null);
  renderRuns([]);
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

function renderRuns(runs) {
  if (!runs.length) {
    runsList.className = "tables-list empty";
    runsList.textContent = "No recent runs yet.";
    return;
  }

  runsList.className = "tables-list";
  runsList.innerHTML = runs
    .map(
      (run) => `
        <article class="table-card">
          <div class="table-meta">
            <span>Run ${run.run_number}</span>
            <span>${escapeHtml(run.status)}</span>
            <span>${escapeHtml(run.validation_status || "pending")}</span>
            <span>${run.attempts} attempt${run.attempts === 1 ? "" : "s"}</span>
            ${run.is_active_run ? "<span>active</span>" : ""}
          </div>
          <strong>${run.failure_stage ? `Failure stage: ${escapeHtml(run.failure_stage)}` : "No recorded failure stage"}</strong>
          <p>${escapeHtml(run.error_message || "No run error recorded.")}</p>
          <div class="artifact-links">
            ${
              run.has_failure_artifact
                ? `<a href="/runs/${run.run_id}/failure-artifact" target="_blank" rel="noreferrer">Failure artifact</a>`
                : '<span class="muted">No failure artifact</span>'
            }
          </div>
        </article>
      `,
    )
    .join("");
}

function renderQualitySummary(summary) {
  if (!summary) {
    qualityEvalCoverageValue.textContent = "0 / 0";
    qualityFailedQueryCountValue.textContent = "0";
    qualityStructuralFailureCountValue.textContent = "0";
    qualityFailedRunCountValue.textContent = "0";
    setFeedback(qualityFeedback, "Unable to load corpus quality summary.");
    return;
  }

  qualityEvalCoverageValue.textContent = `${formatInteger(summary.documents_with_latest_evaluation)} / ${formatInteger(summary.document_count)}`;
  qualityFailedQueryCountValue.textContent = formatInteger(summary.total_failed_queries);
  qualityStructuralFailureCountValue.textContent = formatInteger(
    summary.total_failed_structural_checks,
  );
  qualityFailedRunCountValue.textContent = formatInteger(summary.failed_run_count);
  setFeedback(
    qualityFeedback,
    `${formatInteger(summary.documents_with_failed_queries)} documents have failed retrieval queries, ${formatInteger(summary.documents_with_structural_failures)} have structural check failures, and ${formatInteger(summary.missing_latest_evaluations)} are missing latest evaluations.`,
  );
}

function renderQualityEvaluations(rows) {
  if (!rows.length) {
    qualityEvaluations.className = "tables-list empty";
    qualityEvaluations.textContent = "Latest evaluation state will appear here.";
    return;
  }

  qualityEvaluations.className = "tables-list";
  qualityEvaluations.innerHTML = rows
    .slice(0, 8)
    .map(
      (row) => `
        <article class="table-card">
          <div class="table-meta">
            <span>${escapeHtml(row.evaluation_status)}</span>
            <span>${escapeHtml(row.latest_run_status || "no latest run")}</span>
            <span>${escapeHtml(row.latest_validation_status || "pending")}</span>
          </div>
          <strong>${escapeHtml(row.title || row.source_filename)}</strong>
          <p>${escapeHtml(row.source_filename)}</p>
          <p>${formatInteger(row.failed_queries)} failed queries · ${formatInteger(row.failed_structural_checks)} structural failures</p>
        </article>
      `,
    )
    .join("");
}

function renderQualityFailureStages(stages) {
  if (!stages.length) {
    qualityFailureStages.className = "tables-list empty";
    qualityFailureStages.textContent = "No failed runs grouped by stage.";
    return;
  }

  qualityFailureStages.className = "tables-list";
  qualityFailureStages.innerHTML = stages
    .map(
      (stage) => `
        <article class="table-card">
          <div class="table-meta">
            <span>${escapeHtml(stage.failure_stage)}</span>
            <span>${formatInteger(stage.run_count)} failed run${stage.run_count === 1 ? "" : "s"}</span>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderQualityFailures(payload) {
  if (!payload) {
    qualityFailures.className = "tables-list empty";
    qualityFailures.textContent = "Quality failures will appear here.";
    return;
  }

  const evaluationFailures = payload.evaluation_failures || [];
  const runFailures = payload.run_failures || [];
  const items = [
    ...evaluationFailures.slice(0, 4).map(
      (row) => `
        <article class="table-card">
          <div class="table-meta">
            <span>evaluation</span>
            <span>${escapeHtml(row.evaluation_status)}</span>
          </div>
          <strong>${escapeHtml(row.title || row.source_filename)}</strong>
          <p>${formatInteger(row.failed_queries)} failed queries · ${formatInteger(row.failed_structural_checks)} structural failures</p>
        </article>
      `,
    ),
    ...runFailures.slice(0, 4).map(
      (run) => `
        <article class="table-card">
          <div class="table-meta">
            <span>run ${run.run_number}</span>
            <span>${escapeHtml(run.failure_stage || "missing")}</span>
          </div>
          <strong>${escapeHtml(run.title || run.source_filename)}</strong>
          <p>${escapeHtml(run.error_message || "No run error recorded.")}</p>
        </article>
      `,
    ),
  ];

  if (!items.length) {
    qualityFailures.className = "tables-list empty";
    qualityFailures.textContent = "No quality failures are currently recorded.";
    return;
  }

  qualityFailures.className = "tables-list";
  qualityFailures.innerHTML = items.join("");
}

function renderQualityEvalCandidates(rows) {
  if (!rows.length) {
    qualityEvalCandidates.className = "tables-list empty";
    qualityEvalCandidates.textContent = "Mined evaluation candidates will appear here.";
    return;
  }

  qualityEvalCandidates.className = "tables-list";
  qualityEvalCandidates.innerHTML = rows
    .slice(0, 6)
    .map(
      (row) => `
        <article class="table-card">
          <div class="table-meta">
            <span>${escapeHtml(row.candidate_type)}</span>
            <span>${formatInteger(row.occurrence_count)} seen</span>
            <span>${escapeHtml(row.reason)}</span>
          </div>
          <strong>${escapeHtml(row.query_text)}</strong>
          <p>${escapeHtml(row.source_filename || "whole corpus")}</p>
          <p>${escapeHtml(row.expected_result_type || "no expected type yet")} · ${escapeHtml(row.mode)}</p>
        </article>
      `,
    )
    .join("");
}

function renderQualityTrends(payload) {
  if (!payload) {
    qualityTrends.className = "tables-list empty";
    qualityTrends.textContent = "Search and feedback trends will appear here.";
    return;
  }

  const dayCards = (payload.search_request_days || []).map(
    (point) => `
      <article class="table-card">
        <div class="table-meta">
          <span>${escapeHtml(point.bucket_date)}</span>
          <span>${formatInteger(point.request_count)} searches</span>
          <span>${formatPercent(point.table_hit_rate)}</span>
        </div>
        <p>${formatInteger(point.zero_result_count)} zero-result requests</p>
      </article>
    `,
  );
  const feedbackSummary =
    (payload.feedback_counts || [])
      .slice(0, 4)
      .map((row) => `${row.feedback_type}: ${formatInteger(row.count)}`)
      .join(" · ") || "No search feedback yet.";
  const answerFeedbackSummary =
    (payload.answer_feedback_counts || [])
      .slice(0, 4)
      .map((row) => `${row.feedback_type}: ${formatInteger(row.count)}`)
      .join(" · ") || "No answer feedback yet.";

  qualityTrends.className = "tables-list";
  qualityTrends.innerHTML = [
    `<article class="table-card"><strong>Feedback labels</strong><p>${escapeHtml(feedbackSummary)}</p></article>`,
    `<article class="table-card"><strong>Answer feedback</strong><p>${escapeHtml(answerFeedbackSummary)}</p></article>`,
    ...dayCards,
  ].join("");
}

function renderSearchReplays(rows) {
  state.replayRuns = rows;
  renderReplayCompareOptions(rows);
  if (!rows.length) {
    searchReplays.className = "tables-list empty";
    searchReplays.textContent = "Replay suite runs will appear here.";
    return;
  }

  searchReplays.className = "tables-list";
  searchReplays.innerHTML = rows
    .slice(0, 6)
    .map(
      (row) => `
        <article class="table-card" data-replay-run-id="${escapeHtml(row.replay_run_id)}">
          <div class="table-meta">
            <span>${escapeHtml(row.source_type)}</span>
            <span>${escapeHtml(row.harness_name)}</span>
            <span>${escapeHtml(row.status)}</span>
            <span>${escapeHtml(formatTimestamp(row.created_at))}</span>
          </div>
          <strong>${formatInteger(row.passed_count)} passed / ${formatInteger(row.query_count)} queries</strong>
          <p>${escapeHtml(row.reranker_version)} · ${escapeHtml(row.retrieval_profile_name)} · ${formatInteger(row.failed_count)} failed · ${formatInteger(row.zero_result_count)} zero-result · ${formatInteger(row.top_result_changes)} top-result changes</p>
        </article>
      `,
    )
    .join("");
}

function renderReplayCompareOptions(rows) {
  const compareButton = replayCompareForm.querySelector("button");
  if (!rows.length) {
    replayBaseline.innerHTML = '<option value="">No replay runs yet</option>';
    replayCandidate.innerHTML = '<option value="">No replay runs yet</option>';
    replayBaseline.disabled = true;
    replayCandidate.disabled = true;
    compareButton.disabled = true;
    renderReplayComparison(null);
    return;
  }

  const priorBaseline = replayBaseline.value;
  const priorCandidate = replayCandidate.value;
  const options = rows
    .slice(0, 12)
    .map(
      (row) => `
        <option value="${escapeHtml(row.replay_run_id)}">
          ${escapeHtml(row.source_type)} · ${formatInteger(row.passed_count)}/${formatInteger(row.query_count)} · ${escapeHtml(formatTimestamp(row.created_at))}
        </option>
      `,
    )
    .join("");

  replayBaseline.innerHTML = options;
  replayCandidate.innerHTML = options;

  const fallbackCandidate = rows[0]?.replay_run_id || "";
  const fallbackBaseline =
    rows.find((row) => row.replay_run_id !== fallbackCandidate)?.replay_run_id || fallbackCandidate;

  replayCandidate.value = rows.some((row) => row.replay_run_id === priorCandidate)
    ? priorCandidate
    : fallbackCandidate;
  replayBaseline.value =
    rows.some((row) => row.replay_run_id === priorBaseline) && priorBaseline !== replayCandidate.value
      ? priorBaseline
      : rows.find((row) => row.replay_run_id !== replayCandidate.value)?.replay_run_id ||
        replayCandidate.value;

  const canCompare = rows.length > 1;
  replayBaseline.disabled = !canCompare;
  replayCandidate.disabled = !canCompare;
  compareButton.disabled = !canCompare;
  if (!canCompare) {
    setFeedback(replayFeedback, "Create at least two replay runs to compare ranking changes.");
    renderReplayComparison(null);
  }
}

function renderReplayComparison(payload) {
  if (!payload) {
    replayComparison.className = "tables-list empty";
    replayComparison.textContent = "Replay comparison will appear here.";
    return;
  }

  const changedQueryCards = (payload.changed_queries || []).length
    ? payload.changed_queries.slice(0, 6).map(
        (row) => `
          <article class="table-card">
            <div class="table-meta">
              <span>${escapeHtml(row.mode)}</span>
              <span>${row.baseline_passed ? "baseline passed" : "baseline failed"}</span>
              <span>${row.candidate_passed ? "candidate passed" : "candidate failed"}</span>
            </div>
            <strong>${escapeHtml(row.query_text)}</strong>
            <p>${formatInteger(row.baseline_result_count)} baseline results · ${formatInteger(row.candidate_result_count)} candidate results</p>
          </article>
        `,
      )
    : [
        `<article class="table-card"><strong>No changed shared queries</strong><p>The selected replay runs produced the same pass/fail outcomes for every shared query.</p></article>`,
      ];

  replayComparison.className = "tables-list";
  replayComparison.innerHTML = [
    `
      <article class="table-card">
        <div class="table-meta">
          <span>${formatInteger(payload.shared_query_count)} shared queries</span>
          <span>${formatInteger(payload.improved_count)} improved</span>
          <span>${formatInteger(payload.regressed_count)} regressed</span>
        </div>
        <strong>${formatInteger(payload.unchanged_count)} unchanged queries</strong>
        <p>${formatInteger(payload.baseline_zero_result_count)} baseline zero-result queries · ${formatInteger(payload.candidate_zero_result_count)} candidate zero-result queries</p>
      </article>
    `,
    ...changedQueryCards,
  ].join("");
}

function renderReplayDetail(payload) {
  if (!payload) {
    replayDetail.className = "tables-list empty";
    replayDetail.textContent = "Replay drilldown will appear here.";
    return;
  }

  const queryCards = (payload.query_results || []).length
    ? payload.query_results.slice(0, 8).map(
        (row) => `
          <article class="table-card">
            <div class="table-meta">
              <span>${row.passed ? "passed" : "failed"}</span>
              <span>${escapeHtml(row.mode)}</span>
              <span>${formatInteger(row.result_count)} results</span>
            </div>
            <strong>${escapeHtml(row.query_text)}</strong>
            <p>${escapeHtml(row.details?.source_reason || "replay_query")}</p>
            <p>${formatInteger(row.overlap_count)} overlap · ${formatInteger(row.added_count)} added · ${formatInteger(row.removed_count)} removed · ${formatInteger(row.max_rank_shift)} max rank shift</p>
          </article>
        `,
      )
    : [
        `<article class="table-card"><strong>No replay query rows</strong><p>This replay run persisted without query-level detail rows.</p></article>`,
      ];

  replayDetail.className = "tables-list";
  replayDetail.innerHTML = [
    `
      <article class="table-card">
        <div class="table-meta">
          <span>${escapeHtml(payload.harness_name)}</span>
          <span>${escapeHtml(payload.reranker_version)}</span>
          <span>${escapeHtml(payload.retrieval_profile_name)}</span>
        </div>
        <strong>${formatInteger(payload.passed_count)} passed / ${formatInteger(payload.query_count)} queries</strong>
        <p>${formatInteger(payload.failed_count)} failed · ${formatInteger(payload.zero_result_count)} zero-result · ${formatInteger(payload.top_result_changes)} top-result changes</p>
      </article>
    `,
    ...queryCards,
  ].join("");
}

function renderSearchFeedbackActions(searchRequestId, results) {
  if (!searchRequestId) {
    searchFeedbackActions.innerHTML = "";
    return;
  }

  searchFeedbackActions.innerHTML = `
    <button class="secondary-button" type="button" data-request-feedback="missing_table">Missing table</button>
    <button class="secondary-button" type="button" data-request-feedback="missing_chunk">Missing chunk</button>
    <button class="secondary-button" type="button" data-request-feedback="no_answer">No answer</button>
  `;
  searchFeedbackActions.className = "status-actions";
  if (!results.length) {
    setFeedback(
      searchFeedback,
      `Request ${searchRequestId} logged with no results. Use the request-level labels if the miss is meaningful.`,
    );
  }
}

function renderChatFeedbackActions(chatAnswerId) {
  state.lastChatAnswerId = chatAnswerId;
  if (!chatAnswerId) {
    chatFeedbackActions.innerHTML = "";
    setFeedback(chatFeedback, "");
    return;
  }

  chatFeedbackActions.className = "status-actions";
  chatFeedbackActions.innerHTML = `
    <button class="secondary-button" type="button" data-chat-feedback="helpful">Helpful</button>
    <button class="secondary-button" type="button" data-chat-feedback="unsupported">Unsupported</button>
    <button class="secondary-button" type="button" data-chat-feedback="incomplete">Incomplete</button>
    <button class="secondary-button" type="button" data-chat-feedback="unhelpful">Unhelpful</button>
  `;
}

function renderSearchResults(results, searchRequestId = null) {
  state.lastSearchRequestId = searchRequestId;
  renderSearchFeedbackActions(searchRequestId, results);
  if (!results.length) {
    setFeedback(searchFeedback, searchRequestId ? `Request ${searchRequestId} returned no results.` : "");
    searchResults.className = "search-results empty";
    searchResults.textContent = "No results yet.";
    return;
  }

  setFeedback(
    searchFeedback,
    searchRequestId
      ? `Request ${searchRequestId} persisted ${results.length} ranked result${results.length === 1 ? "" : "s"} for replay.`
      : "",
  );
  searchResults.className = "search-results";
  searchResults.innerHTML = results
    .map((result, index) => {
      const feedbackButtons = searchRequestId
        ? `
          <div class="artifact-links">
            <button class="secondary-button" type="button" data-result-feedback="relevant" data-result-rank="${index + 1}">Relevant</button>
            <button class="secondary-button" type="button" data-result-feedback="irrelevant" data-result-rank="${index + 1}">Irrelevant</button>
          </div>
        `
        : "";
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
            ${feedbackButtons}
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
          ${feedbackButtons}
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
    state.lastChatAnswerId = null;
    chatResponse.className = "chat-response empty";
    chatResponse.textContent = "Answers will appear here.";
    chatCitations.className = "chat-citations empty";
    chatCitations.textContent = "Retrieved support will appear here.";
    setFeedback(chatWarning, "");
    renderChatFeedbackActions(null);
    return;
  }

  renderChatFeedbackActions(payload.chat_answer_id);
  chatResponse.className = "chat-response";
  chatResponse.innerHTML = `
    <article class="answer-card">
      <div class="result-meta">
        <span>${escapeHtml(payload.mode)}</span>
        <span>${payload.used_fallback ? "extractive fallback" : "model-backed answer"}</span>
        <span>${escapeHtml(payload.harness_name || "default_v1")}</span>
        ${payload.model ? `<span>${escapeHtml(payload.model)}</span>` : ""}
      </div>
      <p>${escapeHtml(payload.answer).replaceAll("\n", "<br />")}</p>
    </article>
  `;

  setFeedback(chatWarning, payload.warning || "");
  setFeedback(
    chatFeedback,
    payload.chat_answer_id
      ? `Answer ${payload.chat_answer_id} is persisted with search request ${payload.search_request_id || "unknown"}.`
      : "",
  );

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

async function fetchQualitySummary() {
  const response = await fetch("/quality/summary");
  if (!response.ok) {
    throw new Error("Unable to load quality summary.");
  }
  return response.json();
}

async function fetchQualityEvaluations() {
  const response = await fetch("/quality/evaluations");
  if (!response.ok) {
    throw new Error("Unable to load quality evaluations.");
  }
  return response.json();
}

async function fetchQualityFailures() {
  const response = await fetch("/quality/failures");
  if (!response.ok) {
    throw new Error("Unable to load quality failures.");
  }
  return response.json();
}

async function fetchQualityEvalCandidates() {
  const response = await fetch("/quality/eval-candidates");
  if (!response.ok) {
    throw new Error("Unable to load mined evaluation candidates.");
  }
  return response.json();
}

async function fetchQualityTrends() {
  const response = await fetch("/quality/trends");
  if (!response.ok) {
    throw new Error("Unable to load quality trends.");
  }
  return response.json();
}

async function fetchSearchReplays() {
  const response = await fetch("/search/replays");
  if (!response.ok) {
    throw new Error("Unable to load replay suite runs.");
  }
  return response.json();
}

async function fetchSearchReplayDetail(replayRunId) {
  const response = await fetch(`/search/replays/${replayRunId}`);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail || "Unable to load replay drilldown.");
  }
  return body;
}

async function fetchSearchHarnesses() {
  const response = await fetch("/search/harnesses");
  if (!response.ok) {
    throw new Error("Unable to load search harnesses.");
  }
  return response.json();
}

async function postSearchReplayRun(payload) {
  const response = await fetch("/search/replays", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail || "Unable to run replay suite.");
  }
  return body;
}

async function postChatAnswerFeedback(chatAnswerId, payload) {
  const response = await fetch(`/chat/answers/${chatAnswerId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail || "Unable to record answer feedback.");
  }
  return body;
}

async function fetchSearchReplayComparison(baselineReplayRunId, candidateReplayRunId) {
  const params = new URLSearchParams({
    baseline_replay_run_id: baselineReplayRunId,
    candidate_replay_run_id: candidateReplayRunId,
  });
  const response = await fetch(`/search/replays/compare?${params.toString()}`);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail || "Unable to compare replay runs.");
  }
  return body;
}

async function postSearchFeedback(searchRequestId, payload) {
  const response = await fetch(`/search/requests/${searchRequestId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail || "Unable to record search feedback.");
  }
  return body;
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

async function fetchDocumentRuns(documentId) {
  const response = await fetch(`/documents/${documentId}/runs`);
  if (!response.ok) {
    throw new Error("Unable to load run history.");
  }
  return response.json();
}

async function refreshDocuments() {
  const [documents, metrics] = await Promise.all([fetchDocuments(), fetchMetrics()]);
  const selectionStillExists = documents.some(
    (document) => document.document_id === state.currentDocumentId,
  );
  if (state.currentDocumentId && !selectionStillExists) {
    state.currentDocumentId = null;
  }
  if (!state.currentDocumentId && documents.length && !state.selectionCleared) {
    state.currentDocumentId = documents[0].document_id;
  }
  renderDocuments(documents);
  renderOverview(documents, metrics);
  renderIngestionLane(documents);
  renderTelemetry(metrics);
  syncChatScopeState();
  await refreshQualityPanel();
}

async function refreshQualityPanel() {
  try {
    const [summary, evaluations, failures, evalCandidates, trends, replayRuns] = await Promise.all([
      fetchQualitySummary(),
      fetchQualityEvaluations(),
      fetchQualityFailures(),
      fetchQualityEvalCandidates(),
      fetchQualityTrends(),
      fetchSearchReplays(),
    ]);
    renderQualitySummary(summary);
    renderQualityEvaluations(evaluations);
    renderQualityFailureStages(summary.failed_runs_by_stage || []);
    renderQualityFailures(failures);
    renderQualityEvalCandidates(evalCandidates);
    renderQualityTrends(trends);
    renderSearchReplays(replayRuns);
    if (state.selectedReplayRunId) {
      const replayExists = replayRuns.some((row) => row.replay_run_id === state.selectedReplayRunId);
      if (replayExists) {
        renderReplayDetail(await fetchSearchReplayDetail(state.selectedReplayRunId));
      } else {
        state.selectedReplayRunId = null;
        renderReplayDetail(null);
      }
    }
  } catch (error) {
    renderQualitySummary(null);
    renderQualityEvaluations([]);
    renderQualityFailureStages([]);
    renderQualityFailures(null);
    renderQualityEvalCandidates([]);
    renderQualityTrends(null);
    renderSearchReplays([]);
    renderReplayComparison(null);
    renderReplayDetail(null);
    setFeedback(qualityFeedback, error.message || "Unable to load corpus quality state.");
  }
}

async function refreshCurrentDocument() {
  if (!state.currentDocumentId) {
    resetDocumentSelectionState();
    setFeedback(
      statusFeedback,
      "No document selected. Choose a validated document or run whole-corpus search and chat.",
    );
    syncChatScopeState();
    return;
  }

  try {
    const [document, chunks, tables, figures, evaluation, runs] = await Promise.all([
      fetchDocumentStatus(state.currentDocumentId),
      fetchChunks(state.currentDocumentId),
      fetchTables(state.currentDocumentId),
      fetchFigures(state.currentDocumentId),
      fetchLatestEvaluation(state.currentDocumentId),
      fetchDocumentRuns(state.currentDocumentId),
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
    renderRuns(runs);
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

clearSelectionButton.addEventListener("click", async () => {
  state.currentDocumentId = null;
  state.selectionCleared = true;
  const documents = await fetchDocuments();
  renderDocuments(documents);
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
  state.lastChatAnswerId = null;
  chatResponse.className = "chat-response empty";
  chatResponse.textContent = "Retrieving evidence and building a cited answer...";
  chatCitations.className = "chat-citations empty";
  chatCitations.textContent = "Waiting for supporting passages...";
  setFeedback(chatWarning, "");
  setFeedback(chatFeedback, "");
  renderChatFeedbackActions(null);

  const payload = { question, mode, top_k: 6, harness_name: chatHarness.value || undefined };
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
  state.lastSearchRequestId = null;
  renderSearchFeedbackActions(null, []);
  setFeedback(searchFeedback, "");
  searchResults.className = "search-results empty";
  searchResults.textContent = "Searching...";

  const payload = { query, mode, limit: 8, harness_name: searchHarness.value || undefined };
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
    renderSearchResults(body, response.headers.get("X-Search-Request-Id"));
    finishProcessRail(
      "search",
      true,
      `Direct retrieval completed with ${body.length} ranked result${body.length === 1 ? "" : "s"}.`,
    );
    const metrics = await fetchMetrics();
    renderTelemetry(metrics);
  } catch (error) {
    state.lastSearchRequestId = null;
    renderSearchFeedbackActions(null, []);
    setFeedback(searchFeedback, "");
    searchResults.className = "search-results empty";
    searchResults.textContent = error.message || "Search failed.";
    finishProcessRail("search", false, error.message || "Direct search failed.");
  }
});

searchResults.addEventListener("click", async (event) => {
  if (!(event.target instanceof Element)) {
    return;
  }
  const button = event.target.closest("[data-result-feedback]");
  if (!button || !state.lastSearchRequestId) {
    return;
  }

  try {
    const feedback = await postSearchFeedback(state.lastSearchRequestId, {
      feedback_type: button.dataset.resultFeedback,
      result_rank: Number(button.dataset.resultRank),
    });
    setFeedback(
      searchFeedback,
      `Recorded ${feedback.feedback_type} feedback for request ${feedback.search_request_id}.`,
    );
    await refreshQualityPanel();
  } catch (error) {
    setFeedback(searchFeedback, error.message || "Unable to record search feedback.");
  }
});

searchFeedbackActions.addEventListener("click", async (event) => {
  if (!(event.target instanceof Element)) {
    return;
  }
  const button = event.target.closest("[data-request-feedback]");
  if (!button || !state.lastSearchRequestId) {
    return;
  }

  try {
    const feedback = await postSearchFeedback(state.lastSearchRequestId, {
      feedback_type: button.dataset.requestFeedback,
    });
    setFeedback(
      searchFeedback,
      `Recorded ${feedback.feedback_type} feedback for request ${feedback.search_request_id}.`,
    );
    await refreshQualityPanel();
  } catch (error) {
    setFeedback(searchFeedback, error.message || "Unable to record search feedback.");
  }
});

chatFeedbackActions.addEventListener("click", async (event) => {
  if (!(event.target instanceof Element)) {
    return;
  }
  const button = event.target.closest("[data-chat-feedback]");
  if (!button || !state.lastChatAnswerId) {
    return;
  }

  try {
    const feedback = await postChatAnswerFeedback(state.lastChatAnswerId, {
      feedback_type: button.dataset.chatFeedback,
    });
    setFeedback(
      chatFeedback,
      `Recorded ${feedback.feedback_type} feedback for answer ${feedback.chat_answer_id}.`,
    );
    await refreshQualityPanel();
  } catch (error) {
    setFeedback(chatFeedback, error.message || "Unable to record answer feedback.");
  }
});

replayRunForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    source_type: replaySourceType.value,
    limit: Number(replayLimit.value) || 12,
    harness_name: replayHarness.value || undefined,
  };
  setFeedback(
    replayFeedback,
    `Running ${payload.source_type} replay suite over up to ${formatInteger(payload.limit)} queries...`,
  );

  try {
    const replayRun = await postSearchReplayRun(payload);
    await refreshQualityPanel();
    state.selectedReplayRunId = replayRun.replay_run_id;
    renderReplayDetail(replayRun);
    const baselineOption = Array.from(replayBaseline.options).find(
      (option) => option.value !== replayRun.replay_run_id,
    );
    replayCandidate.value = replayRun.replay_run_id;
    if (baselineOption) {
      replayBaseline.value = baselineOption.value;
    }
    setFeedback(
      replayFeedback,
      `Replay ${replayRun.replay_run_id} completed: ${formatInteger(replayRun.passed_count)} passed / ${formatInteger(replayRun.query_count)} queries.`,
      replayRun.failed_count ? "" : "muted",
    );
  } catch (error) {
    renderReplayComparison(null);
    setFeedback(replayFeedback, error.message || "Unable to run replay suite.");
  }
});

searchReplays.addEventListener("click", async (event) => {
  if (!(event.target instanceof Element)) {
    return;
  }
  const card = event.target.closest("[data-replay-run-id]");
  if (!card) {
    return;
  }

  state.selectedReplayRunId = card.dataset.replayRunId;
  setFeedback(replayFeedback, `Loading replay drilldown for ${state.selectedReplayRunId}...`);
  try {
    const detail = await fetchSearchReplayDetail(state.selectedReplayRunId);
    renderReplayDetail(detail);
    setFeedback(
      replayFeedback,
      `Loaded replay ${detail.replay_run_id} for harness ${detail.harness_name}.`,
    );
  } catch (error) {
    renderReplayDetail(null);
    setFeedback(replayFeedback, error.message || "Unable to load replay drilldown.");
  }
});

replayCompareForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!replayBaseline.value || !replayCandidate.value) {
    setFeedback(replayFeedback, "Choose replay runs before comparing.");
    return;
  }
  if (replayBaseline.value === replayCandidate.value) {
    setFeedback(replayFeedback, "Choose two different replay runs for comparison.");
    return;
  }

  setFeedback(replayFeedback, "Comparing replay runs...");
  try {
    const comparison = await fetchSearchReplayComparison(replayBaseline.value, replayCandidate.value);
    renderReplayComparison(comparison);
    setFeedback(
      replayFeedback,
      `Compared ${comparison.baseline_replay_run_id} to ${comparison.candidate_replay_run_id}. ${formatInteger(comparison.regressed_count)} regressions and ${formatInteger(comparison.improved_count)} improvements across shared queries.`,
      comparison.regressed_count ? "" : "muted",
    );
  } catch (error) {
    renderReplayComparison(null);
    setFeedback(replayFeedback, error.message || "Unable to compare replay runs.");
  }
});

checkHealth();
setArtifactLink(jsonLink, "#", false);
setArtifactLink(yamlLink, "#", false);
syncChatScopeState();
renderChatResponse(null);
renderReplayDetail(null);
resetProcessRail();
fetchSearchHarnesses()
  .then(renderHarnessSelects)
  .catch((error) => {
    setFeedback(statusFeedback, error.message || "Unable to load search harnesses.");
  });
refreshDocuments().then(refreshCurrentDocument);
startPolling();
