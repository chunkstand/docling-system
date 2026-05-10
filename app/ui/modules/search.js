function renderSearchRequestDetail(detailState) {
  const container = byId("search-request-detail");
  if (!container) {
    return;
  }
  if (detailState.error) {
    delete container.dataset.requestId;
    renderEmpty(
      container,
      formatApiError(detailState.error, "Unable to load persisted search request detail."),
    );
    return;
  }
  const detail = detailState.data;
  if (!detail) {
    delete container.dataset.requestId;
    renderEmpty(container, "Run a search or select a persisted request to inspect detail.");
    return;
  }
  container.dataset.requestId = detail.search_request_id;

  const cards = [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(detail.query)}</strong>
          <span class="meta-pill">${escapeHtml(detail.harness_name || DEFAULT_HARNESS_NAME)}</span>
        </header>
        <div class="status-meta">
          <span>${escapeHtml(detail.mode)}</span>
          <span>${formatInteger(detail.candidate_count)} candidates</span>
          <span>${formatInteger(detail.result_count)} results</span>
          <span>${formatInteger(detail.table_hit_count)} table hits</span>
          <span>${detail.duration_ms == null ? "duration unavailable" : `${formatDecimal(detail.duration_ms, 1)} ms`}</span>
        </div>
        <p>${escapeHtml(detail.origin)} request created ${escapeHtml(formatDateTime(detail.created_at))}.</p>
        <p>${escapeHtml(
          detail.embedding_status === "completed"
            ? "Embedding lookup completed for this request."
            : detail.embedding_error
              ? `Embedding status ${detail.embedding_status}: ${detail.embedding_error}`
              : `Embedding status ${detail.embedding_status}.`,
        )}</p>
      </article>
    `,
  ];

  if (Object.keys(detail.filters || {}).length) {
    cards.push(jsonCard("Applied filters", detail.filters, "No filters were applied."));
  }
  cards.push(
    `
      <article class="stack-card">
        <header>
          <strong>Readable request summary</strong>
          <span class="meta-pill">${escapeHtml(detail.retrieval_profile_name || detail.harness_name)}</span>
        </header>
        <p>This ${escapeHtml(detail.mode)} search used the ${escapeHtml(detail.harness_name)} harness, returned ${formatInteger(detail.result_count)} ranked results, and exposed ${formatInteger(detail.table_hit_count)} table hits.</p>
      </article>
    `,
  );

  if (detail.feedback?.length) {
    cards.push(
      ...detail.feedback.map(
        (feedback) => `
          <article class="stack-card">
            <header>
              <strong>${escapeHtml(feedback.feedback_type)}</strong>
              <span class="meta-pill">${feedback.result_rank ? `rank ${feedback.result_rank}` : "request-level"}</span>
            </header>
            <p>${escapeHtml(feedback.note || "No operator note recorded.")}</p>
          </article>
        `,
      ),
    );
  }

  if (detail.results?.length) {
    cards.push(...detail.results.slice(0, 6).map((result) => buildSearchResultCard(result, { logged: true })));
  }

  renderStackCards(container, cards);
}

function renderSearchReplayDetail(replayState) {
  const container = byId("search-replay-detail");
  if (!container) {
    return;
  }
  if (replayState.error) {
    renderEmpty(container, formatApiError(replayState.error, "Unable to replay the selected request."));
    return;
  }
  const replay = replayState.data;
  if (!replay) {
    renderEmpty(container, "Replay output for the selected request will appear here.");
    return;
  }

  renderStackCards(container, [
    `
      <article class="status-card">
        <header>
          <strong>Replay diff</strong>
          <span class="meta-pill">${formatInteger(replay.diff.overlap_count)} overlap</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(replay.diff.added_count)} added</span>
          <span>${formatInteger(replay.diff.removed_count)} removed</span>
          <span>${replay.diff.top_result_changed ? "top result changed" : "top result stable"}</span>
          <span>max rank shift ${formatInteger(replay.diff.max_rank_shift)}</span>
        </div>
        <p>Replay request ${escapeHtml(replay.replay_request.search_request_id)} is now persisted and inspectable.</p>
      </article>
    `,
    ...replay.replay_request.results.slice(0, 6).map((result) => buildSearchResultCard(result, { logged: true })),
  ]);
}

function renderSearchHarnessContext(harnesses) {
  const container = byId("search-harness-context");
  if (!container) {
    return;
  }
  const harnessName = byId("search-harness")?.value || getDefaultHarnessName(harnesses || []);
  const harnessRow = (harnesses || []).find((row) => row.harness_name === harnessName) || {
    harness_name: harnessName,
    retrieval_profile_name: harnessName,
    harness_config: {},
    is_default: harnessName === DEFAULT_HARNESS_NAME,
  };
  const copy = makeHarnessDescription(harnessRow);
  const modeLabel = byId("search-mode")?.selectedOptions?.[0]?.textContent || "Hybrid";
  const documentLabel = byId("search-document")?.selectedOptions?.[0]?.textContent || "Whole validated corpus";
  const typeLabel = byId("search-result-type")?.selectedOptions?.[0]?.textContent || "Chunks and tables";

  renderStackCards(container, [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(copy.title)}</strong>
          <span class="meta-pill">${harnessRow.is_default ? "default harness" : escapeHtml(harnessRow.retrieval_profile_name)}</span>
        </header>
        <div class="status-meta">
          <span>${escapeHtml(modeLabel)}</span>
          <span>${escapeHtml(documentLabel)}</span>
          <span>${escapeHtml(typeLabel)}</span>
        </div>
        <p>${escapeHtml(copy.summary)}</p>
        <p>${escapeHtml(copy.reason)}</p>
      </article>
    `,
  ]);
}

function renderReplayRunList(replayRunsState) {
  const container = byId("search-replay-runs");
  if (!container) {
    return;
  }
  if (replayRunsState.error) {
    renderEmpty(container, formatApiError(replayRunsState.error, "Unable to load replay run summaries."));
    return;
  }
  const replayRuns = replayRunsState.data || [];
  if (!replayRuns.length) {
    renderEmpty(container, "No replay runs are persisted yet.");
    return;
  }

  renderStackCards(
    container,
    replayRuns.map(
      (run) => `
        <button
          type="button"
          class="status-card selectable-card ${uiState.search.selectedReplayRunId === String(run.replay_run_id) ? "is-selected" : ""}"
          data-ui-action="load-replay-run"
          data-replay-run-id="${escapeHtml(run.replay_run_id)}"
        >
          <header>
            <strong>${escapeHtml(run.source_type)}</strong>
            <span class="status-pill ${escapeHtml(run.status)}">${escapeHtml(formatStatusLabel(run.status))}</span>
          </header>
          <div class="status-meta">
            <span>${escapeHtml(run.harness_name)}</span>
            <span>${formatInteger(run.query_count)} queries</span>
            <span>${formatInteger(run.failed_count)} failed</span>
            <span>${formatInteger(run.zero_result_count)} zero-result</span>
          </div>
          <p>Created ${escapeHtml(formatDateTime(run.created_at))}.</p>
        </button>
      `,
    ),
  );
}

function renderReplayRunDetail(detailState) {
  const container = byId("search-replay-run-detail");
  if (!container) {
    return;
  }
  if (detailState.error) {
    renderEmpty(container, formatApiError(detailState.error, "Unable to load replay run detail."));
    return;
  }
  const detail = detailState.data;
  if (!detail) {
    renderEmpty(container, "Select a replay run to inspect per-query detail.");
    return;
  }

  const changed = (detail.query_results || [])
    .filter((row) => !row.passed || row.top_result_changed || row.max_rank_shift > 0)
    .slice(0, 8);

  const cards = [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(detail.source_type)}</strong>
          <span class="meta-pill">${escapeHtml(detail.harness_name)}</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(detail.query_count)} queries</span>
          <span>${formatInteger(detail.passed_count)} passed</span>
          <span>${formatInteger(detail.failed_count)} failed</span>
          <span>${formatInteger(detail.zero_result_count)} zero-result</span>
        </div>
        <p>Replay run ${escapeHtml(detail.replay_run_id)} completed ${escapeHtml(formatDateTime(detail.completed_at || detail.created_at))}.</p>
      </article>
    `,
    detail.summary ? jsonCard("Replay summary", detail.summary) : "",
    ...changed.map(
      (row) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(row.query_text)}</strong>
            <span class="status-pill ${row.passed ? "completed" : "failed"}">${row.passed ? "passed" : "failed"}</span>
          </header>
          <div class="stack-meta">
            <span>${escapeHtml(row.mode)}</span>
            <span>${formatInteger(row.result_count)} results</span>
            <span>${formatInteger(row.max_rank_shift)} rank shift</span>
          </div>
          <p>${escapeHtml(
            row.passed
              ? "This replay stayed acceptable but changed enough to merit inspection."
              : "This replay did not meet the acceptance criteria for the stored expectation.",
          )}</p>
          <pre class="code-block">${escapeHtml(formatJson(row.details || {}))}</pre>
          <div class="artifact-actions">
            ${row.source_search_request_id ? internalLink(`/ui/search.html?request_id=${encodeURIComponent(row.source_search_request_id)}`, "Open source request") : ""}
          </div>
        </article>
      `,
    ),
  ].filter(Boolean);

  renderStackCards(container, cards);
}

async function loadSearchRequestDetail(requestId) {
  if (!requestId) {
    renderSearchRequestDetail({ data: null, error: null });
    return;
  }
  uiState.search.selectedRequestId = String(requestId);
  setQueryParam("request_id", requestId);
  const detailState = await fetchState(`/search/requests/${requestId}`);
  renderSearchRequestDetail(detailState);
  if (detailState.error) {
    recordActivity(
      "Request detail failed",
      formatApiError(detailState.error, "Unable to load persisted search request detail."),
      "error",
    );
  } else if (detailState.data) {
    recordActivity(
      "Request detail loaded",
      `Loaded persisted request ${shortId(requestId)} with ${formatInteger(detailState.data.result_count)} results.`,
      "success",
    );
  }
  return detailState;
}

async function loadReplayRunDetail(replayRunId) {
  if (!replayRunId) {
    renderReplayRunDetail({ data: null, error: null });
    return;
  }
  uiState.search.selectedReplayRunId = String(replayRunId);
  setQueryParam("replay_run_id", replayRunId);
  renderReplayRunList({ data: uiState.search.replayRuns, error: null });
  const detailState = await fetchState(`/search/replays/${replayRunId}`);
  renderReplayRunDetail(detailState);
  if (detailState.error) {
    recordActivity(
      "Replay run failed to load",
      formatApiError(detailState.error, "Unable to load replay run detail."),
      "error",
    );
  } else if (detailState.data) {
    recordActivity(
      "Replay run loaded",
      `Loaded replay run ${shortId(replayRunId)} with ${formatInteger(detailState.data.query_count)} queries.`,
      "success",
    );
  }
}

async function replaySelectedSearchRequest() {
  const requestId = getSelectedSearchRequestId();
  if (!requestId) {
    renderEmpty(byId("search-replay-detail"), "Select a search request first.");
    return;
  }
  renderEmpty(byId("search-replay-detail"), "Replaying the selected request...");
  recordActivity(
    "Replay started",
    `Replaying persisted request ${shortId(requestId)} against the current system state.`,
  );
  const replayState = await fetchState(`/search/requests/${requestId}/replay`, { method: "POST" });
  renderSearchReplayDetail(replayState);
  if (replayState.error) {
    recordActivity("Replay failed", formatApiError(replayState.error, "Replay failed."), "error");
  } else {
    recordActivity(
      "Replay completed",
      `Replay overlap ${formatInteger(replayState.data?.diff?.overlap_count || 0)} with ${formatInteger(replayState.data?.diff?.added_count || 0)} added results.`,
      "success",
    );
  }
  if (replayState.data?.replay_request?.search_request_id) {
    await loadSearchRequestDetail(replayState.data.replay_request.search_request_id);
  }
}

async function loadSearchPage(context) {
  const [harnessState, metricsState, replayRunsState] = await Promise.all([
    getHarnessCatalogState(),
    fetchState("/metrics"),
    fetchState("/search/replays"),
  ]);
  const harnesses = harnessState.data || [];

  const defaultHarness = getDefaultHarnessName(harnesses);
  setText("search-default-harness", defaultHarness);
  setText(
    "search-table-hit-rate",
    metricsState.data ? formatPercent(metricsState.data.mixed_search_table_hit_rate || 0) : "Locked",
  );

  populateHarnessSelect("search-harness", harnesses);
  populateHarnessSelect("replay-suite-harness", harnesses, true);
  const harnessSelect = byId("search-harness");
  if (harnessSelect) {
    harnessSelect.value = defaultHarness;
  }

  const searchDocuments = [
    { document_id: "", title: "Whole validated corpus" },
    ...context.documents,
  ];
  populateSelect(
    byId("search-document"),
    searchDocuments,
    (row) =>
      `<option value="${escapeHtml(row.document_id || "")}">${escapeHtml(
        row.title || row.source_filename || "Whole validated corpus",
      )}</option>`,
    "Whole validated corpus",
  );
  if (uiState.search.selectedDocumentId && byId("search-document")) {
    byId("search-document").value = uiState.search.selectedDocumentId;
  }
  if (harnessState.error) {
    renderEmpty(
      byId("search-harness-list"),
      formatApiError(harnessState.error, "Unable to load harness registry."),
    );
    renderEmpty(
      byId("search-harness-list-tab"),
      formatApiError(harnessState.error, "Unable to load harness registry."),
    );
  } else {
    renderHarnessCards(byId("search-harness-list"), harnesses, true);
    renderHarnessCards(byId("search-harness-list-tab"), harnesses, true);
  }
  uiState.search.replayRuns = replayRunsState.data || [];
  renderReplayRunList(replayRunsState);
  renderSearchHarnessContext(harnesses);
  recordActivity(
    "Search workspace ready",
    `Loaded ${formatInteger(harnesses.length)} harnesses and ${formatInteger(uiState.search.replayRuns.length)} replay runs.`,
    "success",
  );

  [
    "search-harness",
    "search-mode",
    "search-document",
    "search-result-type",
  ].forEach((id) => {
    byId(id)?.addEventListener("change", () => renderSearchHarnessContext(harnesses));
  });

  const form = byId("search-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const filters = {};
    const documentId = byId("search-document")?.value;
    const resultType = byId("search-result-type")?.value;
    if (documentId) {
      filters.document_id = documentId;
      uiState.search.selectedDocumentId = documentId;
      setQueryParam("document_id", documentId);
    }
    if (resultType) {
      filters.result_type = resultType;
    }

    const payload = {
      query: byId("search-query")?.value || "",
      mode: byId("search-mode")?.value || "hybrid",
      limit: Number(byId("search-limit")?.value || 8),
      harness_name: byId("search-harness")?.value || undefined,
    };
    if (Object.keys(filters).length) {
      payload.filters = filters;
    }

    setNote("search-meta", "Running validated-corpus search...");
    recordActivity(
      "Search started",
      `Running ${(payload.harness_name || defaultHarness)} in ${payload.mode} mode.`,
    );
    try {
      const response = await fetch("/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw await parseResponseError(response);
      }
      const results = await response.json();
      const requestId = response.headers.get("X-Search-Request-Id");
      renderResultCards(byId("search-results"), results.map((result) => buildSearchResultCard(result)));
      if (requestId) {
        setNote(
          "search-meta",
          `Search request ${requestId} persisted ${results.length} ranked results for replay.`,
        );
        recordActivity(
          "Search completed",
          `Persisted request ${shortId(requestId)} with ${formatInteger(results.length)} results and ${formatInteger(results.filter((result) => result.result_type === "table").length)} table hits.`,
          "success",
        );
        await loadSearchRequestDetail(requestId);
      } else {
        setNote("search-meta", `Rendered ${results.length} ranked results.`);
        recordActivity(
          "Search completed",
          `Rendered ${formatInteger(results.length)} ranked results without a persisted request id.`,
          "success",
        );
      }
      if (!results.length) {
        renderEmpty(byId("search-results"), "No evidence matched this query under the selected harness.");
        recordActivity(
          "Search returned no results",
          "The selected harness produced no ranked evidence for this query.",
          "error",
        );
      }
    } catch (error) {
      renderEmpty(byId("search-results"), `Search failed: ${formatApiError(error)}`);
      setNote("search-meta", "Search failed.", true);
      recordActivity("Search failed", formatApiError(error, "Search failed."), "error");
    }
  });

  byId("search-feedback-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const requestId = uiState.search.selectedRequestId;
    if (!requestId) {
      setNote("search-feedback-note-inline", "Select a search request first.", true);
      return;
    }
    const rawRank = byId("search-feedback-rank")?.value;
    const payload = {
      feedback_type: byId("search-feedback-type")?.value || "relevant",
      result_rank: rawRank ? Number(rawRank) : null,
      note: byId("search-feedback-note")?.value || null,
    };
    try {
      await fetchJson(`/search/requests/${requestId}/feedback`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setNote("search-feedback-note-inline", "Feedback attached to the selected request.");
      recordActivity(
        "Feedback recorded",
        `Attached ${payload.feedback_type} feedback to request ${shortId(requestId)}.`,
        "success",
      );
      await loadSearchRequestDetail(requestId);
    } catch (error) {
      setNote("search-feedback-note-inline", formatApiError(error, "Feedback failed."), true);
      recordActivity("Feedback failed", formatApiError(error, "Feedback failed."), "error");
    }
  });

  byId("search-replay-request")?.addEventListener("click", async (event) => {
    event.preventDefault();
    await replaySelectedSearchRequest();
  });

  byId("replay-suite-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const harnessName = byId("replay-suite-harness")?.value || null;
    const payload = {
      source_type: byId("replay-suite-source-type")?.value || "evaluation_queries",
      limit: Number(byId("replay-suite-limit")?.value || 12),
      harness_name: harnessName || undefined,
    };
    const runState = await fetchState("/search/replays", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (runState.error) {
      renderEmpty(byId("search-replay-run-detail"), formatApiError(runState.error, "Replay suite failed."));
      recordActivity("Replay suite failed", formatApiError(runState.error, "Replay suite failed."), "error");
      return;
    }
    const refreshedRuns = await fetchState("/search/replays");
    uiState.search.replayRuns = refreshedRuns.data || [];
    renderReplayRunList(refreshedRuns);
    recordActivity(
      "Replay suite completed",
      `Created replay run ${shortId(runState.data?.replay_run_id)} from ${payload.source_type}.`,
      "success",
    );
    await loadReplayRunDetail(runState.data?.replay_run_id);
  });

  if (uiState.search.selectedRequestId) {
    await loadSearchRequestDetail(uiState.search.selectedRequestId);
  }
  if (uiState.search.selectedReplayRunId) {
    await loadReplayRunDetail(uiState.search.selectedReplayRunId);
  }
}

