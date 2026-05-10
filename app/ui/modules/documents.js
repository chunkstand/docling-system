function renderDocumentList() {
  const container = byId("documents-list");
  if (!container) {
    return;
  }
  const filter = uiState.documents.filter.trim().toLowerCase();
  const filtered = uiState.documents.rows.filter((row) => {
    if (!filter) {
      return true;
    }
    const haystack = `${row.title || ""} ${row.source_filename || ""}`.toLowerCase();
    return haystack.includes(filter);
  });

  if (!filtered.length) {
    renderDocumentScopeNote(0);
    renderEmpty(container, "No documents match the current filter.");
    return;
  }

  renderDocumentScopeNote(filtered.length);
  renderStackCards(
    container,
    filtered.map(
      (row) => `
        <button
          type="button"
          class="status-card selectable-card ${uiState.documents.selectedDocumentId === String(row.document_id) ? "is-selected" : ""}"
          data-ui-action="select-document"
          data-document-id="${escapeHtml(row.document_id)}"
        >
          <header>
            <strong>${escapeHtml(row.title || row.source_filename)}</strong>
            <span class="status-pill ${escapeHtml(row.active_run_status || "unknown")}">${escapeHtml(formatStatusLabel(row.active_run_status || "inactive"))}</span>
          </header>
          <div class="status-meta">
            <span>${escapeHtml(row.source_filename)}</span>
            <span>${formatInteger(row.table_count)} tables</span>
            <span>${formatInteger(row.figure_count)} figures</span>
          </div>
          <p>${row.latest_evaluation ? `${formatInteger(row.latest_evaluation.failed_queries)} failed latest-eval queries.` : "No latest evaluation persisted yet."}</p>
        </button>
      `,
    ),
  );
}

function renderDocumentScopeNote(filteredCount) {
  const note = byId("documents-scope-note");
  if (!note) {
    return;
  }
  const loadedCount = uiState.documents.rows.length;
  const totalCount = Number(uiState.documents.totalCount || loadedCount);
  const filterActive = uiState.documents.filter.trim().length > 0;

  if (totalCount > loadedCount) {
    const matchingLabel = filterActive
      ? `${formatInteger(filteredCount)} matching summaries`
      : `${formatInteger(loadedCount)} recent summaries`;
    note.textContent = `Showing ${matchingLabel} from ${formatInteger(loadedCount)} loaded / ${formatInteger(totalCount)} total documents.`;
    return;
  }

  const baselineLabel = filterActive
    ? `${formatInteger(filteredCount)} matching documents`
    : `${formatInteger(loadedCount)} document summaries`;
  note.textContent = `Showing ${baselineLabel}.`;
}

function renderDocumentContext(detailState, runsState, evaluationState) {
  const container = byId("document-context");
  if (!container) {
    return;
  }
  if (detailState.error) {
    renderEmpty(container, formatApiError(detailState.error, "Unable to load document context."));
    return;
  }
  const detail = detailState.data;
  if (!detail) {
    renderEmpty(
      container,
      "Select a document to inspect its active state, promotion posture, and latest quality signal.",
    );
    return;
  }

  const runs = runsState.data || [];
  const latestRun =
    runs.find((row) => String(row.run_id) === String(detail.latest_run_id)) || runs[0] || null;
  const evaluation = evaluationState.data;
  const searchableSummary = detail.is_searchable
    ? "Active validated content is serving search traffic for this document."
    : "This document is not currently searchable because no validated active run is available.";
  const promotionSummary = detail.latest_run_promoted
    ? "The latest run is already promoted."
    : "The latest run has not been promoted into the active corpus yet.";
  const evaluationSummary = evaluation
    ? `${formatInteger(evaluation.passed_queries)} of ${formatInteger(evaluation.query_count)} latest-evaluation queries passed.`
    : "No latest evaluation is persisted for this document yet.";
  const runSummary = latestRun
    ? `Latest run ${formatInteger(latestRun.run_number)} is ${formatStatusLabel(latestRun.status)} and currently at ${formatStatusLabel(latestRun.current_stage || latestRun.status)}.`
    : "No durable run history is loaded for this document.";

  renderStackCards(container, [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(detail.title || detail.source_filename)}</strong>
          <span class="status-pill ${escapeHtml(detail.active_run_status || "unknown")}">${escapeHtml(formatStatusLabel(detail.active_run_status || "inactive"))}</span>
        </header>
        <div class="status-meta">
          <span>${detail.is_searchable ? "searchable" : "not searchable"}</span>
          <span>${detail.latest_run_promoted ? "latest run promoted" : "latest run pending promotion"}</span>
          <span>updated ${escapeHtml(formatDateTime(detail.updated_at))}</span>
        </div>
        <p>${escapeHtml(searchableSummary)}</p>
        <p>${escapeHtml(promotionSummary)}</p>
      </article>
    `,
    `
      <article class="stack-card">
        <header>
          <strong>Readable state summary</strong>
          <span class="meta-pill">${escapeHtml(detail.latest_validation_status || "validation unknown")}</span>
        </header>
        <p>${escapeHtml(runSummary)}</p>
        <p>${escapeHtml(evaluationSummary)}</p>
      </article>
    `,
  ]);
}

function renderDocumentArtifacts(detailState, runsState) {
  const container = byId("document-artifacts");
  if (!container) {
    return;
  }
  if (detailState.error) {
    renderEmpty(container, formatApiError(detailState.error, "Unable to load document artifacts."));
    return;
  }
  const detail = detailState.data;
  if (!detail) {
    renderEmpty(
      container,
      "Select a document to inspect document-level artifacts and failure recovery outputs.",
    );
    return;
  }

  const actions = [
    detail.has_json_artifact
      ? downloadButton(
          "Download docling.json",
          `/documents/${detail.document_id}/artifacts/json`,
          `${detail.source_filename}.docling.json`,
        )
      : "",
    detail.has_yaml_artifact
      ? downloadButton(
          "Download document.yaml",
          `/documents/${detail.document_id}/artifacts/yaml`,
          `${detail.source_filename}.document.yaml`,
        )
      : "",
  ].filter(Boolean);
  const failureRuns = (runsState.data || []).filter((run) => run.has_failure_artifact).slice(0, 4);

  const cards = [
    `
      <article class="status-card">
        <header>
          <strong>Canonical document artifacts</strong>
          <span class="meta-pill">${escapeHtml(detail.source_filename)}</span>
        </header>
        <div class="status-meta">
          <span>${detail.has_json_artifact ? "JSON ready" : "JSON missing"}</span>
          <span>${detail.has_yaml_artifact ? "YAML ready" : "YAML missing"}</span>
          <span>${formatInteger(detail.table_count || 0)} active tables</span>
          <span>${formatInteger(detail.figure_count || 0)} active figures</span>
        </div>
        <p>Document-level artifacts are the operator entry point into the active validated parse. Table and figure artifacts stay inspectable from the Active outputs tab.</p>
        <div class="artifact-actions">${actions.join("") || "<span>No document artifacts are available.</span>"}</div>
      </article>
    `,
  ];

  if (failureRuns.length) {
    cards.push(
      ...failureRuns.map(
        (run) => `
          <article class="stack-card">
            <header>
              <strong>Failure artifact for run ${formatInteger(run.run_number)}</strong>
              <span class="status-pill failed">${escapeHtml(formatStatusLabel(run.failure_stage || run.status))}</span>
            </header>
            <p>${escapeHtml(run.error_message || "Failure artifact recorded without an explicit error message.")}</p>
            <div class="artifact-actions">
              ${downloadButton(
                "Download failure artifact",
                `/runs/${run.run_id}/failure-artifact`,
                `${detail.document_id}-${run.run_id}-failure.json`,
              )}
            </div>
          </article>
        `,
      ),
    );
  } else {
    cards.push(
      `<article class="stack-card"><strong>Failure recovery artifacts</strong><p>No run failure artifacts are currently recorded for this document.</p></article>`,
    );
  }

  renderStackCards(container, cards);
}

function renderDocumentDetail(detailState) {
  const container = byId("document-detail");
  if (!container) {
    return;
  }
  if (detailState.error) {
    renderEmpty(container, formatApiError(detailState.error, "Unable to load document detail."));
    return;
  }
  const detail = detailState.data;
  if (!detail) {
    renderEmpty(container, "Select a document to inspect its detail.");
    return;
  }

  const actions = [
    detail.has_json_artifact
      ? downloadButton(
          "Download docling.json",
          `/documents/${detail.document_id}/artifacts/json`,
          `${detail.source_filename}.docling.json`,
        )
      : "",
    detail.has_yaml_artifact
      ? downloadButton(
          "Download document.yaml",
          `/documents/${detail.document_id}/artifacts/yaml`,
          `${detail.source_filename}.document.yaml`,
        )
      : "",
    internalLink(
      `/ui/search.html?document_id=${encodeURIComponent(detail.document_id)}`,
      "Search this document",
    ),
  ].filter(Boolean);

  renderStackCards(container, [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(detail.title || detail.source_filename)}</strong>
          <span class="status-pill ${escapeHtml(detail.active_run_status || "unknown")}">${escapeHtml(formatStatusLabel(detail.active_run_status || "inactive"))}</span>
        </header>
        <div class="status-meta">
          <span>${escapeHtml(detail.source_filename)}</span>
          <span>${detail.is_searchable ? "searchable" : "not searchable"}</span>
          <span>updated ${escapeHtml(formatDateTime(detail.updated_at))}</span>
        </div>
        <p>${escapeHtml(detail.latest_error_message || "No latest run error message recorded.")}</p>
        <div class="artifact-actions">${actions.join("")}</div>
      </article>
    `,
  ]);
}

function renderDocumentRuns(runsState, documentId) {
  const container = byId("document-runs");
  if (!container) {
    return;
  }
  if (runsState.error) {
    renderEmpty(container, formatApiError(runsState.error, "Unable to load document runs."));
    return;
  }
  const runs = runsState.data || [];
  if (!runs.length) {
    renderEmpty(container, "No runs recorded for this document.");
    return;
  }

  renderStackCards(
    container,
    runs.map((run) => {
      const checks = renderCheckStrip([
        {
          label: run.progress_summary?.artifacts_persisted ? "artifacts persisted" : "artifacts pending",
          state: run.progress_summary?.artifacts_persisted ? "passed" : "neutral",
        },
        {
          label: run.progress_summary?.content_counts_recorded
            ? "content counts recorded"
            : "content counts pending",
          state: run.progress_summary?.content_counts_recorded ? "passed" : "neutral",
        },
        {
          label: run.validation_warning_count
            ? `${formatInteger(run.validation_warning_count)} validation warnings`
            : "no validation warnings",
          state: run.validation_warning_count ? "warning" : "passed",
        },
        run.lease_stale
          ? { label: "lease stale", state: "failed" }
          : run.locked_by
            ? { label: "worker lease active", state: "passed" }
            : null,
      ]);
      const timeline = renderTimeline([
        { label: "queued", time: run.created_at },
        { label: "started", time: run.started_at },
        { label: `${formatStatusLabel(run.current_stage || run.status)} since`, time: run.stage_started_at },
        { label: "completed", time: run.completed_at },
      ]);

      return `
        <article class="status-card">
          <header>
            <strong>Run ${formatInteger(run.run_number)}</strong>
            <span class="status-pill ${escapeHtml(run.status)}">${escapeHtml(formatStatusLabel(run.status))}</span>
          </header>
          <div class="status-meta">
            <span>${run.is_active_run ? "active run" : "historical run"}</span>
            <span>${escapeHtml(run.validation_status || "validation pending")}</span>
            <span>${formatInteger(run.chunk_count || 0)} chunks</span>
            <span>${formatInteger(run.table_count || 0)} tables</span>
            <span>${formatInteger(run.figure_count || 0)} figures</span>
          </div>
          <p>${escapeHtml(run.error_message || `Current stage: ${formatStatusLabel(run.current_stage || run.status)}.`)}</p>
          ${checks}
          ${timeline}
          <div class="artifact-actions">
            ${run.has_failure_artifact ? downloadButton("Failure artifact", `/runs/${run.run_id}/failure-artifact`, `${documentId}-${run.run_id}-failure.json`) : ""}
          </div>
        </article>
      `;
    }),
  );
}

function renderDocumentEvaluation(evaluationState) {
  const container = byId("document-evaluation");
  if (!container) {
    return;
  }
  if (evaluationState.error) {
    if (evaluationState.error.status === 404) {
      renderEmpty(container, "No latest evaluation is persisted for this document yet.");
      return;
    }
    renderEmpty(
      container,
      formatApiError(evaluationState.error, "Unable to load latest evaluation detail."),
    );
    return;
  }
  const evaluation = evaluationState.data;
  if (!evaluation) {
    renderEmpty(container, "No latest evaluation is persisted for this document yet.");
    return;
  }

  const failingQueries = (evaluation.query_results || []).filter((row) => !row.passed).slice(0, 8);
  const cards = [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(evaluation.fixture_name || evaluation.corpus_name)}</strong>
          <span class="status-pill ${escapeHtml(evaluation.status)}">${escapeHtml(formatStatusLabel(evaluation.status))}</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(evaluation.query_count)} queries</span>
          <span>${formatInteger(evaluation.passed_queries)} passed</span>
          <span>${formatInteger(evaluation.failed_queries)} failed</span>
          <span>${formatInteger(evaluation.regressed_queries)} regressed</span>
        </div>
        <p>${escapeHtml(evaluation.error_message || "Latest persisted evaluation loaded successfully.")}</p>
      </article>
    `,
  ];

  if (evaluation.summary) {
    cards.push(jsonCard("Evaluation summary", evaluation.summary));
  }

  if (failingQueries.length) {
    cards.push(
      ...failingQueries.map(
        (row) => `
          <article class="stack-card">
            <header>
              <strong>${escapeHtml(row.query_text)}</strong>
              <span class="status-pill failed">${row.passed ? "passed" : "failed"}</span>
            </header>
            <div class="stack-meta">
              <span>${escapeHtml(row.mode)}</span>
              <span>${escapeHtml(row.expected_result_type || "mixed")}</span>
              <span>candidate rank ${escapeHtml(row.candidate_rank ?? "missing")}</span>
            </div>
            <p>${escapeHtml(
              row.candidate_rank != null
                ? `The expected evidence was found at rank ${row.candidate_rank}. Inspect the structured details for exact match reasoning.`
                : "The expected evidence was not found in the returned results. Inspect the structured details for exact match reasoning.",
            )}</p>
            <pre class="code-block">${escapeHtml(formatJson(row.details || {}))}</pre>
          </article>
        `,
      ),
    );
  }

  renderStackCards(container, cards);
}

function renderDocumentTables(tablesState, documentId) {
  const container = byId("document-tables");
  if (!container) {
    return;
  }
  if (tablesState.loading) {
    renderEmpty(container, "Loading active tables.");
    return;
  }
  if (tablesState.error) {
    renderEmpty(container, formatApiError(tablesState.error, "Unable to load active tables."));
    return;
  }
  if (!tablesState.data) {
    renderEmpty(container, "Open Active outputs to load active tables.");
    return;
  }
  const tables = tablesState.data || [];
  if (!tables.length) {
    renderEmpty(container, "No active tables for this document.");
    return;
  }

  renderStackCards(
    container,
    tables.map(
      (table) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(table.title || table.heading || `Table ${table.table_index}`)}</strong>
            <span class="meta-pill">${escapeHtml(formatPageRange(table.page_from, table.page_to))}</span>
          </header>
          <div class="stack-meta">
            <span>${formatInteger(table.row_count || 0)} rows</span>
            <span>${formatInteger(table.col_count || 0)} cols</span>
            <span>${escapeHtml(table.logical_table_key || "run-scoped table")}</span>
          </div>
          <p>${escapeHtml(table.preview_text || "No table preview recorded.")}</p>
          <div class="artifact-actions">
            ${downloadButton("Table JSON", `/documents/${documentId}/tables/${table.table_id}/artifacts/json`, `${table.table_id}.json`)}
            ${downloadButton("Table YAML", `/documents/${documentId}/tables/${table.table_id}/artifacts/yaml`, `${table.table_id}.yaml`)}
          </div>
        </article>
      `,
    ),
  );
}

function renderDocumentFigures(figuresState, documentId) {
  const container = byId("document-figures");
  if (!container) {
    return;
  }
  if (figuresState.loading) {
    renderEmpty(container, "Loading active figures.");
    return;
  }
  if (figuresState.error) {
    renderEmpty(container, formatApiError(figuresState.error, "Unable to load active figures."));
    return;
  }
  if (!figuresState.data) {
    renderEmpty(container, "Open Active outputs to load active figures.");
    return;
  }
  const figures = figuresState.data || [];
  if (!figures.length) {
    renderEmpty(container, "No active figures for this document.");
    return;
  }

  renderStackCards(
    container,
    figures.map(
      (figure) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(figure.caption || figure.heading || `Figure ${figure.figure_index}`)}</strong>
            <span class="meta-pill">${escapeHtml(formatPageRange(figure.page_from, figure.page_to))}</span>
          </header>
          <div class="stack-meta">
            <span>${escapeHtml(figure.source_figure_ref || "generated figure ref")}</span>
            <span>${figure.confidence == null ? "confidence unknown" : `confidence ${formatDecimal(figure.confidence, 2)}`}</span>
          </div>
          <p>${escapeHtml(figure.heading || "No figure heading recorded.")}</p>
          <div class="artifact-actions">
            ${downloadButton("Figure JSON", `/documents/${documentId}/figures/${figure.figure_id}/artifacts/json`, `${figure.figure_id}.json`)}
            ${downloadButton("Figure YAML", `/documents/${documentId}/figures/${figure.figure_id}/artifacts/yaml`, `${figure.figure_id}.yaml`)}
          </div>
        </article>
      `,
    ),
  );
}

async function loadDocumentOutputs(documentId) {
  if (!documentId) {
    return;
  }
  const key = String(documentId);
  const cached = uiState.documents.outputsByDocumentId.get(key);
  if (cached) {
    renderDocumentTables(cached.tablesState, key);
    renderDocumentFigures(cached.figuresState, key);
    return;
  }

  renderDocumentTables({ loading: true }, key);
  renderDocumentFigures({ loading: true }, key);
  const [tablesState, figuresState] = await Promise.all([
    fetchState(`/documents/${key}/tables`),
    fetchState(`/documents/${key}/figures`),
  ]);
  uiState.documents.outputsByDocumentId.set(key, { tablesState, figuresState });
  if (uiState.documents.selectedDocumentId !== key) {
    return;
  }
  renderDocumentTables(tablesState, key);
  renderDocumentFigures(figuresState, key);
}

async function loadSelectedDocument(documentId) {
  if (!documentId) {
    renderDocumentContext({ data: null, error: null }, { data: null, error: null }, { data: null, error: null });
    renderDocumentDetail({ data: null, error: null });
    renderDocumentRuns({ data: null, error: null });
    renderDocumentEvaluation({ data: null, error: null });
    renderDocumentArtifacts({ data: null, error: null }, { data: null, error: null });
    renderDocumentTables({ data: null, error: null });
    renderDocumentFigures({ data: null, error: null });
    setNote("document-action-note", "Select a document first. Reprocess still flows through the normal validation gate.");
    return;
  }

  uiState.documents.selectedDocumentId = String(documentId);
  setQueryParam("document_id", documentId);
  renderDocumentList();
  recordActivity(
    "Loading document workspace",
    `Refreshing detail for ${describeDocumentSelection(documentId)}.`,
  );

  const [detailState, runsState, evaluationState] = await Promise.all([
    fetchState(`/documents/${documentId}`),
    fetchState(`/documents/${documentId}/runs`),
    fetchState(`/documents/${documentId}/evaluations/latest`),
  ]);

  renderDocumentContext(detailState, runsState, evaluationState);
  renderDocumentDetail(detailState);
  renderDocumentRuns(runsState, documentId);
  renderDocumentEvaluation(evaluationState);
  renderDocumentArtifacts(detailState, runsState);
  const outputsState = uiState.documents.outputsByDocumentId.get(String(documentId));
  renderDocumentTables(outputsState?.tablesState || { data: null, error: null }, documentId);
  renderDocumentFigures(outputsState?.figuresState || { data: null, error: null }, documentId);
  if (byId("documents-outputs")?.hidden === false) {
    await loadDocumentOutputs(documentId);
  }

  if (detailState.error) {
    recordActivity(
      "Document load failed",
      formatApiError(detailState.error, "Unable to load document detail."),
      "error",
    );
    return;
  }

  const detail = detailState.data;
  recordActivity(
    "Document workspace ready",
    `${detail?.title || detail?.source_filename || "Document"} loaded with ${formatInteger((runsState.data || []).length)} runs.`,
    "success",
  );
}

async function loadDocumentsPage(context) {
  const corpusDocumentCount = Number(context.qualitySummary?.document_count || context.documents.length);
  uiState.documents.rows = context.documents;
  uiState.documents.totalCount = corpusDocumentCount;
  setText("documents-total-count", formatInteger(corpusDocumentCount));
  setText(
    "documents-searchable-count",
    formatInteger(context.documents.filter((row) => row.active_run_id != null).length),
  );
  setText(
    "documents-table-count",
    formatInteger(context.documents.reduce((sum, row) => sum + (row.table_count || 0), 0)),
  );
  setText(
    "documents-figure-count",
    formatInteger(context.documents.reduce((sum, row) => sum + (row.figure_count || 0), 0)),
  );

  if (context.states.documents.error) {
    renderEmpty(
      byId("documents-list"),
      formatApiError(context.states.documents.error, "Unable to load documents."),
    );
    return;
  }

  const filterInput = byId("documents-filter");
  filterInput?.addEventListener("input", (event) => {
    uiState.documents.filter = event.target.value || "";
    renderDocumentList();
  });

  renderDocumentList();
  const initialId =
    uiState.documents.selectedDocumentId || context.documents[0]?.document_id || null;
  recordActivity(
    "Documents loaded",
    `Loaded ${formatInteger(context.documents.length)} document summaries into the browser slice.`,
    "success",
  );
  await loadSelectedDocument(initialId);

  byId("document-reprocess")?.addEventListener("click", async () => {
    const documentId = uiState.documents.selectedDocumentId;
    if (!documentId) {
      setNote(
        "document-action-note",
        "Select a document first. Reprocess still flows through the normal validation gate.",
      );
      return;
    }
    try {
      const payload = await fetchJson(`/documents/${documentId}/reprocess`, { method: "POST" });
      setNote(
        "document-action-note",
        `Queued reprocess run ${payload.run_id} for the selected document.`,
      );
      recordActivity(
        "Reprocess queued",
        `Queued run ${shortId(payload.run_id)} for ${describeDocumentSelection(documentId)}.`,
        "success",
      );
      await loadSelectedDocument(documentId);
    } catch (error) {
      setNote("document-action-note", formatApiError(error, "Reprocess failed."), true);
      recordActivity(
        "Reprocess failed",
        formatApiError(error, "Reprocess failed."),
        "error",
      );
    }
  });
}

