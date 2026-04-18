const page = document.body.dataset.page;

const harnessCopy = {
  default_v1: {
    title: "default_v1",
    summary: "Production baseline tuned for stable mixed retrieval over active chunks and tables.",
    reason: "Use it when you want the safest default behavior and the reference point for all comparisons.",
  },
  wide_v2: {
    title: "wide_v2",
    summary: "Wider retrieval profile that increases candidate recall before reranking.",
    reason: "Agents compare against it when they suspect the default is missing evidence too early.",
  },
  prose_v3: {
    title: "prose_v3",
    summary: "Prose-oriented experiment that expands candidate generation for prose-heavy questions.",
    reason: "Agents use it when regressions look like context loss or cross-document prose ranking issues.",
  },
};
const DEFAULT_HARNESS_NAME = "default_v1";
let harnessCatalogPromise = null;

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
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

function formatDecimal(value, digits = 2) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value ?? 0);
}

function formatStatusLabel(status) {
  return String(status ?? "unknown").replaceAll("_", " ");
}

function formatShortDate(value) {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function fetchMaybe(url) {
  try {
    return await fetchJson(url);
  } catch (_error) {
    return null;
  }
}

async function getHarnessCatalog() {
  if (!harnessCatalogPromise) {
    harnessCatalogPromise = fetchMaybe("/search/harnesses").then((rows) => rows || []);
  }
  return harnessCatalogPromise;
}

function getDefaultHarnessName(harnesses) {
  return harnesses.find((row) => row.is_default)?.harness_name || DEFAULT_HARNESS_NAME;
}

function setText(id, value) {
  const element = byId(id);
  if (element) {
    element.textContent = value;
  }
}

function renderEmpty(container, message) {
  if (!container) {
    return;
  }
  container.className = container.className.replace(/\bresult-grid\b|\bstack-list\b|\bmini-grid\b/g, "").trim();
  container.classList.add("empty-state");
  container.innerHTML = escapeHtml(message);
}

function renderStackCards(container, cards) {
  if (!container) {
    return;
  }
  if (!cards.length) {
    renderEmpty(container, "No rows to show.");
    return;
  }
  container.className = "stack-list";
  container.innerHTML = cards.join("");
}

function renderResultCards(container, cards) {
  if (!container) {
    return;
  }
  if (!cards.length) {
    renderEmpty(container, "No results to show.");
    return;
  }
  container.className = "result-grid";
  container.innerHTML = cards.join("");
}

function makeHarnessDescription(row) {
  const builtIn = harnessCopy[row.harness_name];
  if (builtIn) {
    return builtIn;
  }
  const metadata = row.harness_config?.metadata || {};
  const base = row.harness_config?.base_harness_name || "custom base";
  if (metadata.override_type === "applied_harness_config_update") {
    return {
      title: row.harness_name,
      summary: `Applied review harness derived from ${base}.`,
      reason: "Published only after a verified draft and explicit approval.",
    };
  }
  return {
    title: row.harness_name,
    summary: "Additional registered retrieval harness.",
    reason: "Treat it as a reviewable configuration with explicit retrieval and reranking behavior.",
  };
}

function renderHarnessCards(container, harnesses, compact = false) {
  if (!container) {
    return;
  }
  if (!harnesses?.length) {
    renderEmpty(container, "Harnesses will appear here.");
    return;
  }
  container.className = compact ? "stack-list" : "feature-grid";
  container.innerHTML = harnesses
    .map((row) => {
      const copy = makeHarnessDescription(row);
      return `
        <article class="${compact ? "stack-card" : "feature-card"}">
          <header>
            <strong>${escapeHtml(copy.title)}</strong>
            <span class="meta-pill">${row.is_default ? "default" : escapeHtml(row.retrieval_profile_name)}</span>
          </header>
          <p>${escapeHtml(copy.summary)}</p>
          <p>${escapeHtml(copy.reason)}</p>
        </article>
      `;
    })
    .join("");
}

function renderDecisionSignals(container, rows) {
  if (!container) {
    return;
  }
  if (!rows?.length) {
    renderEmpty(container, "No decision signals are currently recorded.");
    return;
  }
  renderStackCards(
    container,
    rows.map(
      (row) => `
        <article class="status-card">
          <header>
            <strong>${escapeHtml(row.task_type)}</strong>
            <span class="status-pill ${escapeHtml(row.status)}">${escapeHtml(formatStatusLabel(row.status))}</span>
          </header>
          <div class="status-meta">
            <span>${escapeHtml(row.workflow_version)}</span>
            <span>${escapeHtml(row.threshold_crossed)}</span>
          </div>
          <p>${escapeHtml(row.reason)}</p>
          <p><strong>Recommended action:</strong> ${escapeHtml(row.recommended_action)}</p>
        </article>
      `,
    ),
  );
}

function renderActiveTasks(container, tasks) {
  if (!container) {
    return;
  }
  if (!tasks?.length) {
    renderEmpty(container, "No active agent tasks right now.");
    return;
  }
  renderStackCards(
    container,
    tasks.map(
      (task) => `
        <article class="status-card">
          <header>
            <strong>${escapeHtml(task.task_type)}</strong>
            <span class="status-pill ${escapeHtml(task.status)}">${escapeHtml(formatStatusLabel(task.status))}</span>
          </header>
          <div class="status-meta">
            <span>${escapeHtml(task.workflow_version)}</span>
            <span>priority ${escapeHtml(task.priority)}</span>
            <span>${task.requires_approval ? "approval-gated" : "auto-run"}</span>
          </div>
          <p>${escapeHtml(task.side_effect_level)} workflow with durable lineage and replayable inputs.</p>
        </article>
      `,
    ),
  );
}

function renderValueDensity(container, rows) {
  if (!container) {
    return;
  }
  if (!rows?.length) {
    renderEmpty(container, "Value density will appear here.");
    return;
  }
  renderStackCards(
    container,
    rows.map(
      (row) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(row.task_type)}</strong>
            <span class="meta-pill">${escapeHtml(row.workflow_version)}</span>
          </header>
          <p>${formatInteger(row.downstream_improved_count)} downstream improvements across ${formatInteger(row.recommendation_task_count)} recommendation tasks.</p>
          <p>${formatPercent(row.downstream_improvement_rate)} improvement rate · ${row.improvements_per_dollar == null ? "pricing not integrated" : `${formatDecimal(row.improvements_per_dollar, 2)} improvements / dollar`}</p>
          <div class="value-bar"><span style="width:${Math.min(100, Math.max(12, (row.downstream_improvement_rate || 0) * 100))}%"></span></div>
        </article>
      `,
    ),
  );
}

function buildSearchResultCard(result) {
  const label = result.result_type === "table" ? "Table evidence" : "Chunk evidence";
  const title = result.result_type === "table" ? result.table_title || result.table_heading || "Untitled table" : result.heading || "Prose chunk";
  const body = result.result_type === "table" ? result.table_preview || "" : result.chunk_text || "";
  return `
    <article class="result-card">
      <header>
        <strong>${escapeHtml(title)}</strong>
        <span class="meta-pill">${escapeHtml(label)}</span>
      </header>
      <div class="result-meta">
        <span>${escapeHtml(result.source_filename)}</span>
        <span>${escapeHtml(result.page_from ?? "?" )}${result.page_to && result.page_to !== result.page_from ? `-${escapeHtml(result.page_to)}` : ""}</span>
        <span>score ${formatDecimal(result.score, 3)}</span>
      </div>
      <p>${escapeHtml(body)}</p>
    </article>
  `;
}

function populateSelect(select, rows, formatter, fallbackLabel) {
  if (!select) {
    return;
  }
  if (!rows?.length) {
    select.innerHTML = `<option value="">${escapeHtml(fallbackLabel)}</option>`;
    return;
  }
  select.innerHTML = rows.map(formatter).join("");
}

async function loadGlobalChrome() {
  const [health, documents, qualitySummary, agentSummary] = await Promise.all([
    fetchMaybe("/health"),
    fetchMaybe("/documents"),
    fetchMaybe("/quality/summary"),
    fetchMaybe("/agent-tasks/analytics/summary"),
  ]);

  const validatedCount = (documents || []).filter(
    (row) => row.latest_validation_status === "passed",
  ).length;

  setText("global-health", health?.status === "ok" ? "Ready" : "Offline");
  setText("global-validated", formatInteger(validatedCount));
  setText("global-backlog", formatInteger(agentSummary?.awaiting_approval_count || 0));

  return { documents: documents || [], qualitySummary, agentSummary };
}

async function loadLandingPage(context) {
  const [decisionSignals] = await Promise.all([fetchMaybe("/agent-tasks/analytics/decision-signals")]);
  setText("landing-doc-count", formatInteger(context.documents.length));
  setText(
    "landing-eval-coverage",
    `${formatInteger(context.qualitySummary?.documents_with_latest_evaluation || 0)} / ${formatInteger(context.qualitySummary?.document_count || 0)}`,
  );
  setText("landing-agent-count", formatInteger(context.agentSummary?.task_count || 0));
  setText("landing-signal-count", formatInteger(decisionSignals?.length || 0));
  renderDecisionSignals(byId("landing-decision-signals"), decisionSignals || []);
}

async function loadSearchPage(context) {
  const [harnesses, metrics] = await Promise.all([
    getHarnessCatalog(),
    fetchMaybe("/metrics"),
  ]);

  const defaultHarness = getDefaultHarnessName(harnesses);
  setText("search-default-harness", defaultHarness);
  setText(
    "search-table-hit-rate",
    formatPercent(metrics?.mixed_search_table_hit_rate || 0),
  );

  populateSelect(
    byId("search-harness"),
    harnesses,
    (row) =>
      `<option value="${escapeHtml(row.harness_name)}">${escapeHtml(row.harness_name)}</option>`,
    "No harnesses available",
  );
  const harnessSelect = byId("search-harness");
  if (harnessSelect) {
    harnessSelect.value = defaultHarness;
  }
  populateSelect(
    byId("search-document"),
    [{ document_id: "", title: "Whole validated corpus" }, ...context.documents],
    (row) =>
      `<option value="${escapeHtml(row.document_id || "")}">${escapeHtml(
        row.title || row.source_filename || "Whole validated corpus",
      )}</option>`,
    "Whole validated corpus",
  );
  renderHarnessCards(byId("search-harness-list"), harnesses, true);

  const form = byId("search-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const meta = byId("search-meta");
    const resultsNode = byId("search-results");
    if (meta) {
      meta.textContent = "Running validated-corpus search...";
    }

    const filters = {};
    const documentId = byId("search-document")?.value;
    const resultType = byId("search-result-type")?.value;
    if (documentId) {
      filters.document_id = documentId;
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

    try {
      const response = await fetch("/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const results = await response.json();
      const requestId = response.headers.get("X-Search-Request-Id");
      renderResultCards(byId("search-results"), results.map(buildSearchResultCard));
      if (meta) {
        meta.textContent = requestId
          ? `Search request ${requestId} persisted ${results.length} ranked results for replay.`
          : `Rendered ${results.length} ranked results.`;
      }
      if (!results.length) {
        renderEmpty(resultsNode, "No evidence matched this query under the selected harness.");
      }
    } catch (error) {
      renderEmpty(byId("search-results"), `Search failed: ${error.message}`);
      if (meta) {
        meta.textContent = "Search failed.";
      }
    }
  });
}

function renderQualitySummary(summary) {
  const container = byId("quality-summary-cards");
  if (!container || !summary) {
    renderEmpty(container, "Unable to load quality summary.");
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

function renderQualityFailures(payload) {
  const container = byId("quality-failures");
  if (!container) {
    return;
  }
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

function renderEvalCandidates(rows) {
  renderStackCards(
    byId("eval-candidates"),
    (rows || []).slice(0, 8).map(
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

function renderQualityTrends(payload) {
  const container = byId("quality-trends");
  if (!container) {
    return;
  }
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
  renderStackCards(
    container,
    [
      `<article class="stack-card"><strong>Feedback labels</strong><p>${escapeHtml(feedbackSummary)}</p></article>`,
      ...dayCards,
    ],
  );
}

function renderVerificationTrends(payload) {
  renderStackCards(
    byId("verification-trends"),
    (payload?.series || []).slice(-5).map(
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

function renderHarnessEvaluation(payload) {
  const container = byId("harness-eval-results");
  if (!container) {
    return;
  }
  if (!payload) {
    renderEmpty(container, "Harness evaluation results will appear here.");
    return;
  }
  const cards = [
    `
      <article class="result-card">
        <header>
          <strong>${escapeHtml(payload.candidate_harness_name)} vs ${escapeHtml(payload.baseline_harness_name)}</strong>
          <span class="meta-pill">${formatInteger(payload.total_shared_query_count)} shared queries</span>
        </header>
        <p>${formatInteger(payload.total_improved_count)} improved · ${formatInteger(payload.total_regressed_count)} regressed · ${formatInteger(payload.total_unchanged_count)} unchanged.</p>
      </article>
    `,
    ...(payload.sources || []).map(
      (source) => `
        <article class="result-card">
          <header>
            <strong>${escapeHtml(source.source_type)}</strong>
            <span class="meta-pill">${formatInteger(source.shared_query_count)} shared</span>
          </header>
          <p>${escapeHtml(payload.baseline_harness_name)}: ${formatInteger(source.baseline_passed_count)}/${formatInteger(source.baseline_query_count)} passed · MRR ${formatDecimal(source.baseline_mrr, 3)}</p>
          <p>${escapeHtml(payload.candidate_harness_name)}: ${formatInteger(source.candidate_passed_count)}/${formatInteger(source.candidate_query_count)} passed · MRR ${formatDecimal(source.candidate_mrr, 3)}</p>
        </article>
      `,
    ),
  ];
  renderResultCards(container, cards);
}

async function loadEvalsPage(context) {
  const [qualityFailures, qualityCandidates, qualityTrends, verificationTrends, decisionSignals, harnesses] =
    await Promise.all([
      fetchMaybe("/quality/failures"),
      fetchMaybe("/quality/eval-candidates"),
      fetchMaybe("/quality/trends"),
      fetchMaybe("/agent-tasks/analytics/verifications"),
      fetchMaybe("/agent-tasks/analytics/decision-signals"),
      getHarnessCatalog(),
    ]);

  setText(
    "eval-coverage",
    `${formatInteger(context.qualitySummary?.documents_with_latest_evaluation || 0)} / ${formatInteger(context.qualitySummary?.document_count || 0)}`,
  );
  setText("eval-failed-queries", formatInteger(context.qualitySummary?.total_failed_queries || 0));
  setText(
    "eval-verification-pass",
    formatInteger((verificationTrends?.series || []).reduce((sum, row) => sum + (row.passed_count || 0), 0)),
  );

  renderQualitySummary(context.qualitySummary);
  renderQualityFailures(qualityFailures);
  renderEvalCandidates(qualityCandidates);
  renderQualityTrends(qualityTrends);
  renderVerificationTrends(verificationTrends);
  renderDecisionSignals(byId("eval-decision-signals"), decisionSignals || []);

  populateSelect(
    byId("harness-eval-baseline"),
    harnesses,
    (row) => `<option value="${escapeHtml(row.harness_name)}">${escapeHtml(row.harness_name)}</option>`,
    "No harnesses available",
  );
  populateSelect(
    byId("harness-eval-candidate"),
    harnesses,
    (row) => `<option value="${escapeHtml(row.harness_name)}">${escapeHtml(row.harness_name)}</option>`,
    "No harnesses available",
  );
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

  const form = byId("harness-eval-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const sourceTypes = Array.from(
      document.querySelectorAll("#harness-eval-sources input:checked"),
    ).map((input) => input.value);
    try {
      const payload = await fetchJson("/search/harness-evaluations", {
        method: "POST",
        body: JSON.stringify({
          baseline_harness_name: byId("harness-eval-baseline")?.value,
          candidate_harness_name: byId("harness-eval-candidate")?.value,
          limit: Number(byId("harness-eval-limit")?.value || 12),
          source_types: sourceTypes,
        }),
      });
      renderHarnessEvaluation(payload);
    } catch (error) {
      renderEmpty(byId("harness-eval-results"), `Harness evaluation failed: ${error.message}`);
    }
  });
}

async function loadAgentsPage() {
  const activeStatuses = [
    "processing",
    "queued",
    "retry_wait",
    "blocked",
    "awaiting_approval",
  ]
    .map((status) => `status=${encodeURIComponent(status)}`)
    .join("&");
  const [activeTasks, recommendationSummary, decisionSignals, valueDensity, harnesses] =
    await Promise.all([
      fetchMaybe(`/agent-tasks?${activeStatuses}&limit=24`),
      fetchMaybe("/agent-tasks/analytics/recommendations"),
      fetchMaybe("/agent-tasks/analytics/decision-signals"),
      fetchMaybe("/agent-tasks/analytics/value-density"),
      getHarnessCatalog(),
    ]);

  setText("agent-active-count", formatInteger(activeTasks?.length || 0));
  setText(
    "agent-improvement-rate",
    formatPercent(recommendationSummary?.downstream_improvement_rate || 0),
  );
  setText("agent-signal-count", formatInteger(decisionSignals?.length || 0));

  renderActiveTasks(byId("active-agent-tasks"), activeTasks || []);
  renderDecisionSignals(byId("agent-decision-signals"), decisionSignals || []);
  renderValueDensity(byId("agent-value-density"), valueDensity || []);
  renderHarnessCards(byId("agent-harnesses"), harnesses, false);
}

async function init() {
  const context = await loadGlobalChrome();

  if (page === "landing") {
    await loadLandingPage(context);
    return;
  }
  if (page === "search") {
    await loadSearchPage(context);
    return;
  }
  if (page === "evals") {
    await loadEvalsPage(context);
    return;
  }
  if (page === "agents") {
    await loadAgentsPage(context);
  }
}

void init();
