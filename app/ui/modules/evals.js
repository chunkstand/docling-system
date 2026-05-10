function renderQualitySummary(summaryState) {
  const container = byId("quality-summary-cards");
  if (!container) {
    return;
  }
  if (summaryState.error) {
    renderEmpty(container, formatApiError(summaryState.error, "Unable to load quality summary."));
    return;
  }
  const summary = summaryState.data;
  if (!summary) {
    renderEmpty(container, "Quality summary is unavailable.");
    return;
  }
  container.className = "mini-grid";
  container.innerHTML = `
    <article class="summary-card">
      <strong>${formatInteger(summary.document_count || 0)}</strong>
      <p>Documents in the current governed corpus.</p>
    </article>
    <article class="summary-card">
      <strong>${formatInteger(summary.total_failed_queries || 0)}</strong>
      <p>Failed latest-evaluation queries.</p>
    </article>
    <article class="summary-card">
      <strong>${formatInteger(summary.total_failed_structural_checks || 0)}</strong>
      <p>Structural check failures in the latest evaluation view.</p>
    </article>
    <article class="summary-card">
      <strong>${formatInteger(summary.failed_run_count || 0)}</strong>
      <p>Failed runs still preserved for inspection.</p>
    </article>
  `;
}

function renderQualityFailures(payloadState) {
  const container = byId("quality-failures");
  if (!container) {
    return;
  }
  if (payloadState.error) {
    renderEmpty(container, formatApiError(payloadState.error, "Unable to load quality failures."));
    return;
  }
  const payload = payloadState.data;
  const evaluationFailures = payload?.evaluation_failures || [];
  const runFailures = payload?.run_failures || [];
  const cards = [
    ...evaluationFailures.slice(0, 4).map(
      (row) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(row.title || row.source_filename)}</strong>
            <span class="meta-pill">${escapeHtml(row.evaluation_status)}</span>
          </header>
          <p>${formatInteger(row.failed_queries)} failed queries · ${formatInteger(row.failed_structural_checks)} structural failures.</p>
        </article>
      `,
    ),
    ...runFailures.slice(0, 4).map(
      (run) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(run.title || run.source_filename)}</strong>
            <span class="status-pill failed">${escapeHtml(formatStatusLabel(run.failure_stage || "failed"))}</span>
          </header>
          <p>${escapeHtml(run.error_message || "No run error message recorded.")}</p>
        </article>
      `,
    ),
  ];
  renderStackCards(container, cards);
}

function renderEvalCandidates(rowsState) {
  const container = byId("eval-candidates");
  if (!container) {
    return;
  }
  if (rowsState.error) {
    renderEmpty(container, formatApiError(rowsState.error, "Unable to load evaluation candidates."));
    return;
  }
  renderStackCards(
    container,
    (rowsState.data || []).slice(0, 8).map(
      (row) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(row.query_text)}</strong>
            <span class="meta-pill">${escapeHtml(row.candidate_type)}</span>
          </header>
          <div class="stack-meta">
            <span>${escapeHtml(row.reason)}</span>
            <span>${escapeHtml(row.mode)}</span>
            <span>${formatInteger(row.occurrence_count)} seen</span>
          </div>
          <p>${escapeHtml(row.source_filename || "Whole corpus")}</p>
        </article>
      `,
    ),
  );
}

function renderQualityTrends(payloadState) {
  const container = byId("quality-trends");
  if (!container) {
    return;
  }
  if (payloadState.error) {
    renderEmpty(container, formatApiError(payloadState.error, "Unable to load quality trends."));
    return;
  }
  const payload = payloadState.data;
  const feedbackSummary =
    (payload?.feedback_counts || [])
      .map((row) => `${row.feedback_type}: ${formatInteger(row.count)}`)
      .join(" · ") || "No search feedback yet.";
  const dayCards = (payload?.search_request_days || []).slice(0, 5).map(
    (row) => `
      <article class="stack-card">
        <header>
          <strong>${escapeHtml(row.bucket_date)}</strong>
          <span class="meta-pill">${formatInteger(row.request_count)} searches</span>
        </header>
        <p>${formatPercent(row.table_hit_rate)} table-hit rate · ${formatInteger(row.zero_result_count)} zero-result requests.</p>
      </article>
    `,
  );
  renderStackCards(container, [
    `<article class="stack-card"><strong>Feedback labels</strong><p>${escapeHtml(feedbackSummary)}</p></article>`,
    ...dayCards,
  ]);
}

function renderVerificationTrends(payloadState) {
  const container = byId("verification-trends");
  if (!container) {
    return;
  }
  if (payloadState.error) {
    renderEmpty(
      container,
      formatApiError(payloadState.error, "Unable to load verification trends."),
    );
    return;
  }
  renderStackCards(
    container,
    (payloadState.data?.series || []).slice(-5).map(
      (row) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(formatShortDate(row.bucket_start))}</strong>
            <span class="meta-pill">${formatInteger(row.passed_count)} passed</span>
          </header>
          <p>${formatInteger(row.failed_count)} failed · ${formatInteger(row.error_count)} errored verifications.</p>
        </article>
      `,
    ),
  );
}

function renderHarnessEvaluation(payloadState) {
  const container = byId("harness-eval-results");
  if (!container) {
    return;
  }
  if (payloadState.error) {
    renderEmpty(container, formatApiError(payloadState.error, "Harness evaluation failed."));
    return;
  }
  const payload = payloadState.data;
  if (!payload) {
    renderEmpty(container, "Harness evaluation results will appear here.");
    return;
  }
  const cards = [
    `
      <article class="result-card">
        <header>
          <strong>${escapeHtml(payload.candidate_harness_name)} vs ${escapeHtml(payload.baseline_harness_name)}</strong>
          <span class="status-pill ${escapeHtml(payload.status)}">${escapeHtml(formatStatusLabel(payload.status))}</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(payload.total_shared_query_count)} shared queries</span>
          <span>${payload.evaluation_id ? `eval ${escapeHtml(String(payload.evaluation_id).slice(0, 8))}` : "transient eval"}</span>
          <span>${escapeHtml(formatDateTime(payload.completed_at || payload.created_at))}</span>
        </div>
        <p>${formatInteger(payload.total_improved_count)} improved · ${formatInteger(payload.total_regressed_count)} regressed · ${formatInteger(payload.total_unchanged_count)} unchanged.</p>
        ${payload.error_message ? `<p>${escapeHtml(payload.error_message)}</p>` : ""}
        ${renderCheckStrip([
          {
            label: `${formatInteger(payload.total_improved_count)} improved`,
            state: payload.total_improved_count > 0 ? "passed" : "neutral",
          },
          {
            label: `${formatInteger(payload.total_regressed_count)} regressed`,
            state: payload.total_regressed_count > 0 ? "failed" : "passed",
          },
        ])}
      </article>
    `,
    ...(payload.sources || []).map(
      (source) => `
        <article class="result-card">
          <header>
            <strong>${escapeHtml(source.source_type)}</strong>
            <span class="meta-pill">${formatInteger(source.shared_query_count)} shared</span>
          </header>
          <div class="comparison-grid">
            ${renderMetricComparison("Passed queries", source.baseline_passed_count, source.candidate_passed_count)}
            ${renderMetricComparison("MRR", source.baseline_mrr, source.candidate_mrr, { digits: 3 })}
            ${renderMetricComparison("Table hits", source.baseline_table_hit_count, source.candidate_table_hit_count)}
            ${renderMetricComparison("Zero-result queries", source.baseline_zero_result_count, source.candidate_zero_result_count, { preferLower: true })}
          </div>
          <p>${escapeHtml(payload.baseline_harness_name)} replay ${shortId(source.baseline_replay_run_id)} vs ${escapeHtml(payload.candidate_harness_name)} replay ${shortId(source.candidate_replay_run_id)}.</p>
          ${renderCheckStrip([
            {
              label: `${formatInteger(source.improved_count)} improved`,
              state: source.improved_count > 0 ? "passed" : "neutral",
            },
            {
              label: `${formatInteger(source.regressed_count)} regressed`,
              state: source.regressed_count > 0 ? "failed" : "passed",
            },
            {
              label: `${formatInteger(source.unchanged_count)} unchanged`,
              state: "neutral",
            },
          ])}
          ${renderAcceptanceChecks(source.acceptance_checks)}
          <div class="artifact-actions">
            ${internalLink(`/ui/search.html?replay_run_id=${encodeURIComponent(source.baseline_replay_run_id)}`, "Open baseline replay")}
            ${internalLink(`/ui/search.html?replay_run_id=${encodeURIComponent(source.candidate_replay_run_id)}`, "Open candidate replay")}
          </div>
        </article>
      `,
    ),
  ];
  renderResultCards(container, cards);
}

function renderHarnessEvaluationHistory(historyState) {
  const container = byId("harness-eval-history");
  if (!container) {
    return;
  }
  if (historyState.error) {
    renderEmpty(
      container,
      formatApiError(historyState.error, "Unable to load harness evaluation history."),
    );
    return;
  }
  const evaluations = historyState.data || [];
  if (!evaluations.length) {
    renderEmpty(container, "No harness evaluations have been persisted yet.");
    return;
  }

  renderStackCards(
    container,
    evaluations.map(
      (evaluation) => `
        <button
          type="button"
          class="status-card selectable-card ${uiState.evals.selectedHarnessEvaluationId === String(evaluation.evaluation_id) ? "is-selected" : ""}"
          data-ui-action="load-harness-evaluation"
          data-harness-evaluation-id="${escapeHtml(evaluation.evaluation_id)}"
        >
          <header>
            <strong>${escapeHtml(evaluation.candidate_harness_name)} vs ${escapeHtml(evaluation.baseline_harness_name)}</strong>
            <span class="status-pill ${escapeHtml(evaluation.status)}">${escapeHtml(formatStatusLabel(evaluation.status))}</span>
          </header>
          <div class="status-meta">
            <span>${formatInteger(evaluation.total_shared_query_count)} shared</span>
            <span>${formatInteger(evaluation.total_improved_count)} improved</span>
            <span>${formatInteger(evaluation.total_regressed_count)} regressed</span>
          </div>
          <p>${escapeHtml(formatDateTime(evaluation.completed_at || evaluation.created_at))}${evaluation.error_message ? ` · ${escapeHtml(evaluation.error_message)}` : ""}</p>
        </button>
      `,
    ),
  );
}

async function loadHarnessEvaluationDetail(evaluationId) {
  if (!evaluationId) {
    renderHarnessEvaluation({ data: null });
    return;
  }
  uiState.evals.selectedHarnessEvaluationId = String(evaluationId);
  const detailState = await fetchState(`/search/harness-evaluations/${evaluationId}`);
  renderHarnessEvaluation(detailState);
  const historyState = await fetchState("/search/harness-evaluations?limit=8");
  renderHarnessEvaluationHistory(historyState);
}

function renderEvalContextSummary(context, qualityFailuresState, decisionSignalsState) {
  const container = byId("eval-context-summary");
  if (!container) {
    return;
  }
  if (context.states.qualitySummary.error) {
    renderEmpty(
      container,
      formatApiError(context.states.qualitySummary.error, "Unable to load quality posture."),
    );
    return;
  }
  const summary = context.qualitySummary;
  if (!summary) {
    renderEmpty(container, "Quality posture context is unavailable.");
    return;
  }
  const failureCount =
    (qualityFailuresState.data?.evaluation_failures || []).length +
    (qualityFailuresState.data?.run_failures || []).length;
  const signalCount = (decisionSignalsState.data || []).length;
  renderStackCards(container, [
    `
      <article class="status-card">
        <header>
          <strong>Corpus quality summary</strong>
          <span class="meta-pill">${formatInteger(summary.document_count || 0)} documents</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(summary.documents_with_latest_evaluation || 0)} with latest evaluation</span>
          <span>${formatInteger(summary.total_failed_queries || 0)} failed queries</span>
          <span>${formatInteger(summary.failed_run_count || 0)} failed runs</span>
        </div>
        <p>${signalCount ? `${formatInteger(signalCount)} decision signals need review.` : "No decision signals are currently blocking review."}</p>
        <p>${failureCount ? `${formatInteger(failureCount)} failure rows are visible in the current quality slice.` : "No failure rows are currently visible in the loaded quality slice."}</p>
      </article>
    `,
  ]);
}

async function loadEvalsPage(context) {
  const [
    qualityFailuresState,
    qualityCandidatesState,
    qualityTrendsState,
    verificationTrendsState,
    decisionSignalsState,
    harnessState,
    harnessEvaluationHistoryState,
  ] =
    await Promise.all([
      fetchState("/quality/failures"),
      fetchState("/quality/eval-candidates"),
      fetchState("/quality/trends"),
      fetchState("/agent-tasks/analytics/verifications"),
      fetchState("/agent-tasks/analytics/decision-signals"),
      getHarnessCatalogState(),
      fetchState("/search/harness-evaluations?limit=8"),
    ]);
  const harnesses = harnessState.data || [];

  setText(
    "eval-coverage",
    `${formatInteger(context.qualitySummary?.documents_with_latest_evaluation || 0)} / ${formatInteger(context.qualitySummary?.document_count || 0)}`,
  );
  setText("eval-failed-queries", formatInteger(context.qualitySummary?.total_failed_queries || 0));
  setText(
    "eval-verification-pass",
    formatInteger(
      (verificationTrendsState.data?.series || []).reduce(
        (sum, row) => sum + (row.passed_count || 0),
        0,
      ),
    ),
  );

  renderQualitySummary(context.states.qualitySummary);
  renderQualityFailures(qualityFailuresState);
  renderEvalCandidates(qualityCandidatesState);
  renderQualityTrends(qualityTrendsState);
  renderVerificationTrends(verificationTrendsState);
  renderDecisionSignals(byId("eval-decision-signals"), decisionSignalsState.data || []);
  renderHarnessEvaluationHistory(harnessEvaluationHistoryState);
  if (uiState.evals.selectedHarnessEvaluationId) {
    await loadHarnessEvaluationDetail(uiState.evals.selectedHarnessEvaluationId);
  }
  renderEvalContextSummary(context, qualityFailuresState, decisionSignalsState);
  recordActivity(
    "Evaluation workspace ready",
    `Loaded quality posture for ${formatInteger(context.qualitySummary?.document_count || 0)} documents with ${formatInteger((decisionSignalsState.data || []).length)} decision signals.`,
    "success",
  );

  populateHarnessSelect("harness-eval-baseline", harnesses);
  populateHarnessSelect("harness-eval-candidate", harnesses);
  const baselineSelect = byId("harness-eval-baseline");
  const candidateSelect = byId("harness-eval-candidate");
  const defaultHarness = getDefaultHarnessName(harnesses);
  if (baselineSelect) {
    baselineSelect.value = defaultHarness;
  }
  if (candidateSelect) {
    const candidateHarness =
      harnesses.find((row) => row.harness_name !== defaultHarness)?.harness_name ||
      defaultHarness;
    candidateSelect.value = candidateHarness;
  }

  byId("harness-eval-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const sourceTypes = Array.from(
      document.querySelectorAll("#harness-eval-sources input:checked"),
    ).map((input) => input.value);
    const payloadState = await fetchState("/search/harness-evaluations", {
      method: "POST",
      body: JSON.stringify({
        baseline_harness_name: byId("harness-eval-baseline")?.value,
        candidate_harness_name: byId("harness-eval-candidate")?.value,
        limit: Number(byId("harness-eval-limit")?.value || 12),
        source_types: sourceTypes,
      }),
    });
    renderHarnessEvaluation(payloadState);
    if (!payloadState.error && payloadState.data?.evaluation_id) {
      uiState.evals.selectedHarnessEvaluationId = String(payloadState.data.evaluation_id);
    }
    renderHarnessEvaluationHistory(await fetchState("/search/harness-evaluations?limit=8"));
    if (payloadState.error) {
      recordActivity(
        "Harness evaluation failed",
        formatApiError(payloadState.error, "Harness evaluation failed."),
        "error",
      );
    } else {
      recordActivity(
        "Harness evaluation completed",
        `${payloadState.data?.candidate_harness_name || "Candidate"} improved ${formatInteger(payloadState.data?.total_improved_count || 0)} shared queries and regressed ${formatInteger(payloadState.data?.total_regressed_count || 0)}.`,
        "success",
      );
    }
  });
}

