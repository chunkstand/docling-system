const page = document.body.dataset.page;
const queryParams = new URLSearchParams(window.location.search);

const UI_AUTH_STORAGE_KEY = "docling-system-ui-auth-v1";
const DEFAULT_HARNESS_NAME = "default_v1";
const harnessCopy = {
  default_v1: {
    title: "default_v1",
    summary: "Production baseline tuned for stable mixed retrieval over active chunks and tables.",
    reason:
      "Use it when you want the safest default behavior and the reference point for all comparisons.",
  },
  wide_v2: {
    title: "wide_v2",
    summary: "Wider retrieval profile that increases candidate recall before reranking.",
    reason:
      "Agents compare against it when they suspect the default is missing evidence too early.",
  },
  prose_v3: {
    title: "prose_v3",
    summary: "Prose-oriented experiment that expands candidate generation for prose-heavy questions.",
    reason:
      "Agents use it when regressions look like context loss or cross-document prose ranking issues.",
  },
};

class ApiError extends Error {
  constructor(message, { status = 0, code = null, context = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.context = context;
  }
}

const uiState = {
  auth: loadStoredAuth(),
  harnessCatalogPromise: null,
  documents: {
    rows: [],
    totalCount: 0,
    selectedDocumentId: queryParams.get("document_id"),
    filter: "",
  },
  search: {
    selectedDocumentId: queryParams.get("document_id"),
    selectedRequestId: queryParams.get("request_id"),
    selectedReplayRunId: queryParams.get("replay_run_id"),
    replayRuns: [],
  },
  evals: {
    selectedHarnessEvaluationId: queryParams.get("harness_evaluation_id"),
  },
  agents: {
    selectedTaskId: queryParams.get("task_id"),
    activeTasks: [],
    recentTasks: [],
    activeTasksError: null,
    recentTasksError: null,
  },
};

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

function formatDateTime(value) {
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
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatPageRange(pageFrom, pageTo) {
  if (pageFrom == null && pageTo == null) {
    return "Pages unknown";
  }
  if (pageTo == null || pageFrom === pageTo) {
    return `Page ${pageFrom ?? pageTo}`;
  }
  return `Pages ${pageFrom}-${pageTo}`;
}

function formatJson(value) {
  if (value == null) {
    return "{}";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch (_error) {
    return String(value);
  }
}

function loadStoredAuth() {
  try {
    const raw = window.localStorage.getItem(UI_AUTH_STORAGE_KEY);
    if (!raw) {
      return { scheme: "x-api-key", credential: "" };
    }
    const parsed = JSON.parse(raw);
    return {
      scheme: parsed?.scheme === "bearer" ? "bearer" : "x-api-key",
      credential: String(parsed?.credential || ""),
    };
  } catch (_error) {
    return { scheme: "x-api-key", credential: "" };
  }
}

function saveStoredAuth(auth) {
  uiState.auth = {
    scheme: auth.scheme === "bearer" ? "bearer" : "x-api-key",
    credential: String(auth.credential || "").trim(),
  };
  window.localStorage.setItem(UI_AUTH_STORAGE_KEY, JSON.stringify(uiState.auth));
}

function clearStoredAuth() {
  uiState.auth = { scheme: "x-api-key", credential: "" };
  window.localStorage.removeItem(UI_AUTH_STORAGE_KEY);
}

function buildAuthHeaders() {
  const { scheme, credential } = uiState.auth;
  if (!credential) {
    return {};
  }
  if (scheme === "bearer") {
    return { Authorization: `Bearer ${credential}` };
  }
  return { "X-API-Key": credential };
}

function authLabel() {
  if (!uiState.auth.credential) {
    return "Local / anon";
  }
  return uiState.auth.scheme === "bearer" ? "Bearer stored" : "Key stored";
}

function runtimeApiMode(runtime) {
  return runtime?.api_mode || "local";
}

function runtimeBindLabel(runtime) {
  const host = runtime?.api_host || window.location.hostname || "loopback";
  const port = runtime?.api_port || window.location.port || "";
  return port ? `${host}:${port}` : host;
}

function runtimeAuthMode(runtime) {
  if (runtime?.remote_api_auth_mode) {
    return runtime.remote_api_auth_mode;
  }
  return runtimeApiMode(runtime) === "remote" ? "configured" : "local";
}

function isAuthError(error) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

function formatApiError(error, fallback = "Request failed.") {
  if (!error) {
    return fallback;
  }
  if (isAuthError(error)) {
    return error.message || "Credential or capability required for this surface.";
  }
  return error.message || fallback;
}

async function parseResponseError(response) {
  const contentType = response.headers.get("content-type") || "";
  let payload = null;
  let detail = "";

  if (contentType.includes("application/json")) {
    try {
      payload = await response.json();
    } catch (_error) {
      payload = null;
    }
  } else {
    detail = (await response.text()).trim();
  }

  if (payload) {
    const rawDetail = payload.detail ?? payload.message ?? payload.error ?? payload;
    if (typeof rawDetail === "string") {
      detail = rawDetail;
    } else {
      detail = JSON.stringify(rawDetail);
    }
  }

  return new ApiError(detail || `Request failed: ${response.status}`, {
    status: response.status,
    code: payload?.error_code || payload?.code || null,
    context: payload?.error_context || null,
  });
}

async function fetchJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const authHeaders = buildAuthHeaders();
  for (const [name, value] of Object.entries(authHeaders)) {
    headers.set(name, value);
  }

  if (!(options.body instanceof FormData) && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw await parseResponseError(response);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

async function fetchState(url, options = {}) {
  try {
    return { data: await fetchJson(url, options), error: null };
  } catch (error) {
    return { data: null, error };
  }
}

async function downloadProtectedResource(path, fallbackName = "download") {
  const headers = new Headers(buildAuthHeaders());
  const response = await fetch(path, { headers });
  if (!response.ok) {
    throw await parseResponseError(response);
  }

  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}

function setText(id, value) {
  const element = byId(id);
  if (element) {
    element.textContent = value;
  }
}

function setNote(id, message, isError = false) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.textContent = message;
  element.classList.toggle("error-note", Boolean(isError));
}

function setQueryParam(name, value) {
  const url = new URL(window.location.href);
  if (value) {
    url.searchParams.set(name, value);
  } else {
    url.searchParams.delete(name);
  }
  window.history.replaceState({}, "", url);
}

function renderEmpty(container, message) {
  if (!container) {
    return;
  }
  container.className = container.className
    .replace(/\bresult-grid\b|\bstack-list\b|\bmini-grid\b|\bfeature-grid\b/g, "")
    .trim();
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

function jsonCard(title, payload, emptyMessage = "No structured payload recorded.") {
  const body = payload && Object.keys(payload).length
    ? `<pre class="code-block">${escapeHtml(formatJson(payload))}</pre>`
    : `<p>${escapeHtml(emptyMessage)}</p>`;
  return `
    <article class="stack-card">
      <header>
        <strong>${escapeHtml(title)}</strong>
        <span class="meta-pill">JSON</span>
      </header>
      ${body}
    </article>
  `;
}

function downloadButton(label, path, name) {
  return `
    <button
      type="button"
      class="secondary-link button-link compact-button"
      data-ui-action="download"
      data-download-path="${escapeHtml(path)}"
      data-download-name="${escapeHtml(name)}"
    >
      ${escapeHtml(label)}
    </button>
  `;
}

function internalLink(path, label) {
  return `<a class="inline-link" href="${escapeHtml(path)}">${escapeHtml(label)}</a>`;
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

function buildSearchResultCard(result, { logged = false } = {}) {
  const label = result.result_type === "table" ? "Table evidence" : "Chunk evidence";
  const title =
    result.result_type === "table"
      ? result.table_title || result.table_heading || "Untitled table"
      : result.heading || "Prose chunk";
  const body = result.result_type === "table" ? result.table_preview || "" : result.chunk_text || "";
  const rankMeta = logged && result.rank ? `<span>rank ${formatInteger(result.rank)}</span>` : "";
  const docLink = internalLink(
    `/ui/documents.html?document_id=${encodeURIComponent(result.document_id)}`,
    "Open document",
  );

  return `
    <article class="result-card">
      <header>
        <strong>${escapeHtml(title)}</strong>
        <span class="meta-pill">${escapeHtml(label)}</span>
      </header>
      <div class="result-meta">
        <span>${escapeHtml(result.source_filename)}</span>
        <span>${escapeHtml(formatPageRange(result.page_from, result.page_to))}</span>
        ${rankMeta}
        <span>score ${formatDecimal(result.score, 3)}</span>
      </div>
      <p>${escapeHtml(body)}</p>
      <div class="artifact-actions">
        ${docLink}
      </div>
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

function populateHarnessSelect(selectId, harnesses, includeAny = false) {
  const select = byId(selectId);
  if (!select) {
    return;
  }
  const rows = includeAny ? [{ harness_name: "", is_default: false }, ...harnesses] : harnesses;
  populateSelect(
    select,
    rows,
    (row) =>
      `<option value="${escapeHtml(row.harness_name || "")}">${escapeHtml(
        row.harness_name || "Default harness",
      )}</option>`,
    "Default harness",
  );
}

async function getHarnessCatalogState() {
  if (!uiState.harnessCatalogPromise) {
    uiState.harnessCatalogPromise = fetchState("/search/harnesses");
  }
  return uiState.harnessCatalogPromise;
}

function getDefaultHarnessName(harnesses) {
  return harnesses.find((row) => row.is_default)?.harness_name || DEFAULT_HARNESS_NAME;
}

function getSelectedSearchRequestId() {
  return (
    uiState.search.selectedRequestId ||
    byId("search-request-detail")?.dataset.requestId ||
    new URLSearchParams(window.location.search).get("request_id")
  );
}

function renderAuthControls(context) {
  const form = byId("auth-form");
  const scheme = byId("auth-scheme");
  const credential = byId("auth-credential");
  const clearButton = byId("auth-clear");

  if (!form || !scheme || !credential || !clearButton) {
    return;
  }

  scheme.value = uiState.auth.scheme;
  credential.value = uiState.auth.credential;

  let note = "Anonymous access only works against loopback-local mode.";
  if (context.runtimeStatus) {
    const runtime = context.runtimeStatus;
    const principalCount = runtime.remote_api_principals?.length || 0;
    const authMode = runtimeAuthMode(runtime);
    note = `Runtime ${runtimeApiMode(runtime)} on ${runtimeBindLabel(runtime)}. Auth mode ${authMode}${principalCount ? ` with ${principalCount} principal${principalCount === 1 ? "" : "s"}` : ""}.`;
  } else if (context.authRequired && !uiState.auth.credential) {
    note = "Protected API routes are active. Save an API key or bearer token to unlock the current system.";
  } else if (uiState.auth.credential) {
    note = "Stored credential is applied to all UI requests, including protected artifact downloads.";
  }
  setNote("auth-note", note, false);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    saveStoredAuth({
      scheme: scheme.value,
      credential: credential.value,
    });
    window.location.reload();
  });

  clearButton.addEventListener("click", () => {
    clearStoredAuth();
    window.location.reload();
  });
}

async function loadGlobalChrome() {
  const [healthState, qualityState, agentState, runtimeState] = await Promise.all([
    fetchState("/health"),
    fetchState("/quality/summary"),
    fetchState("/agent-tasks/analytics/summary"),
    fetchState("/runtime/status"),
  ]);
  const documentsState = await fetchState("/documents");

  const documents = documentsState.data || [];
  const authRequired = [documentsState, qualityState, agentState].some((state) =>
    isAuthError(state.error),
  );
  const evalCoverageLabel =
    qualityState.data?.document_count != null
      ? `${formatInteger(qualityState.data?.documents_with_latest_evaluation || 0)} / ${formatInteger(qualityState.data?.document_count || 0)}`
      : formatInteger(documents.filter((row) => row.active_run_id != null).length);

  setText("global-health", healthState.data?.status === "ok" ? "Ready" : "Offline");
  setText("global-validated", evalCoverageLabel);
  setText("global-backlog", formatInteger(agentState.data?.awaiting_approval_count || 0));
  setText("global-auth", authRequired && !uiState.auth.credential ? "Required" : authLabel());

  return {
    documents,
    qualitySummary: qualityState.data,
    agentSummary: agentState.data,
    runtimeStatus: runtimeState.data,
    authRequired,
    states: {
      health: healthState,
      documents: documentsState,
      qualitySummary: qualityState,
      agentSummary: agentState,
      runtimeStatus: runtimeState,
    },
  };
}

function renderDecisionSignals(container, rows, emptyMessage = "No decision signals are currently recorded.") {
  if (!container) {
    return;
  }
  if (!rows?.length) {
    renderEmpty(container, emptyMessage);
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

function renderLandingRuntime(context) {
  const container = byId("landing-runtime");
  if (!container) {
    return;
  }
  const runtime = context.runtimeStatus;
  if (runtime) {
    renderStackCards(container, [
      `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(runtimeApiMode(runtime))} mode</strong>
            <span class="status-pill ${runtime.is_current ? "completed" : "failed"}">${runtime.is_current ? "current" : "stale"}</span>
          </header>
          <div class="stack-meta">
            <span>${escapeHtml(runtimeBindLabel(runtime))}</span>
            <span>${escapeHtml(runtime.process_identity || "api")}</span>
            <span>${escapeHtml(runtimeAuthMode(runtime))}</span>
          </div>
          <p>Startup fingerprint ${escapeHtml(runtime.startup_code_fingerprint || "unknown")}.</p>
          <p>Desired fingerprint ${escapeHtml(runtime.desired_code_fingerprint || "unknown")}.</p>
        </article>
      `,
      jsonCard("Remote principals", runtime.remote_api_principals || runtime.remote_api_capabilities || {}, "Runtime status does not include remote principal details for this mode."),
    ]);
    return;
  }

  renderEmpty(
    container,
    formatApiError(
      context.states.runtimeStatus.error,
      "Runtime status is unavailable for the current credential.",
    ),
  );
}

async function loadLandingPage(context) {
  const decisionSignalsState = await fetchState("/agent-tasks/analytics/decision-signals");
  setText(
    "landing-doc-count",
    formatInteger(context.qualitySummary?.document_count || context.documents.length),
  );
  setText(
    "landing-eval-coverage",
    `${formatInteger(context.qualitySummary?.documents_with_latest_evaluation || 0)} / ${formatInteger(context.qualitySummary?.document_count || 0)}`,
  );
  setText("landing-agent-count", formatInteger(context.agentSummary?.task_count || 0));
  setText("landing-signal-count", formatInteger(decisionSignalsState.data?.length || 0));
  renderDecisionSignals(byId("landing-decision-signals"), decisionSignalsState.data || []);
  renderLandingRuntime(context);
}

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
    runs.map(
      (run) => `
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
          <p>${escapeHtml(run.error_message || run.current_stage || "No run error or current stage recorded.")}</p>
          <div class="artifact-actions">
            ${run.has_failure_artifact ? downloadButton("Failure artifact", `/runs/${run.run_id}/failure-artifact`, `${documentId}-${run.run_id}-failure.json`) : ""}
          </div>
        </article>
      `,
    ),
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
            <p>${escapeHtml(formatJson(row.details || {}))}</p>
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
  if (tablesState.error) {
    renderEmpty(container, formatApiError(tablesState.error, "Unable to load active tables."));
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
  if (figuresState.error) {
    renderEmpty(container, formatApiError(figuresState.error, "Unable to load active figures."));
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

async function loadSelectedDocument(documentId) {
  if (!documentId) {
    renderDocumentDetail({ data: null, error: null });
    renderDocumentRuns({ data: null, error: null });
    renderDocumentEvaluation({ data: null, error: null });
    renderDocumentTables({ data: null, error: null });
    renderDocumentFigures({ data: null, error: null });
    setNote("document-action-note", "Select a document first. Reprocess still flows through the normal validation gate.");
    return;
  }

  uiState.documents.selectedDocumentId = String(documentId);
  setQueryParam("document_id", documentId);
  renderDocumentList();

  const [detailState, runsState, evaluationState, tablesState, figuresState] = await Promise.all([
    fetchState(`/documents/${documentId}`),
    fetchState(`/documents/${documentId}/runs`),
    fetchState(`/documents/${documentId}/evaluations/latest`),
    fetchState(`/documents/${documentId}/tables`),
    fetchState(`/documents/${documentId}/figures`),
  ]);

  renderDocumentDetail(detailState);
  renderDocumentRuns(runsState, documentId);
  renderDocumentEvaluation(evaluationState);
  renderDocumentTables(tablesState, documentId);
  renderDocumentFigures(figuresState, documentId);
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
      await loadSelectedDocument(documentId);
    } catch (error) {
      setNote("document-action-note", formatApiError(error, "Reprocess failed."), true);
    }
  });
}

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
      </article>
    `,
  ];

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
          <p>${escapeHtml(formatJson(row.details || {}))}</p>
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
}

async function replaySelectedSearchRequest() {
  const requestId = getSelectedSearchRequestId();
  if (!requestId) {
    renderEmpty(byId("search-replay-detail"), "Select a search request first.");
    return;
  }
  renderEmpty(byId("search-replay-detail"), "Replaying the selected request...");
  const replayState = await fetchState(`/search/requests/${requestId}/replay`, { method: "POST" });
  renderSearchReplayDetail(replayState);
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
  } else {
    renderHarnessCards(byId("search-harness-list"), harnesses, true);
  }
  uiState.search.replayRuns = replayRunsState.data || [];
  renderReplayRunList(replayRunsState);

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
        await loadSearchRequestDetail(requestId);
      } else {
        setNote("search-meta", `Rendered ${results.length} ranked results.`);
      }
      if (!results.length) {
        renderEmpty(byId("search-results"), "No evidence matched this query under the selected harness.");
      }
    } catch (error) {
      renderEmpty(byId("search-results"), `Search failed: ${formatApiError(error)}`);
      setNote("search-meta", "Search failed.", true);
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
      await loadSearchRequestDetail(requestId);
    } catch (error) {
      setNote("search-feedback-note-inline", formatApiError(error, "Feedback failed."), true);
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
      return;
    }
    const refreshedRuns = await fetchState("/search/replays");
    uiState.search.replayRuns = refreshedRuns.data || [];
    renderReplayRunList(refreshedRuns);
    await loadReplayRunDetail(runState.data?.replay_run_id);
  });

  if (uiState.search.selectedRequestId) {
    await loadSearchRequestDetail(uiState.search.selectedRequestId);
  }
  if (uiState.search.selectedReplayRunId) {
    await loadReplayRunDetail(uiState.search.selectedReplayRunId);
  }
}

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
  });
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
        <button
          type="button"
          class="status-card selectable-card ${uiState.agents.selectedTaskId === String(task.task_id) ? "is-selected" : ""}"
          data-ui-action="select-task"
          data-task-id="${escapeHtml(task.task_id)}"
        >
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
        </button>
      `,
    ),
  );
}

function renderTaskDetail(detailState) {
  const container = byId("agent-task-detail");
  if (!container) {
    return;
  }
  if (detailState.error) {
    renderEmpty(container, formatApiError(detailState.error, "Unable to load task detail."));
    return;
  }
  const detail = detailState.data;
  if (!detail) {
    renderEmpty(container, "Select a task to inspect its durable detail.");
    return;
  }

  const artifactButtons = [
    downloadButton(
      "Context YAML",
      `/agent-tasks/${detail.task_id}/context?format=yaml`,
      `${detail.task_id}-context.yaml`,
    ),
    detail.failure_artifact_path
      ? downloadButton(
          "Failure artifact",
          `/agent-tasks/${detail.task_id}/failure-artifact`,
          `${detail.task_id}-failure.json`,
        )
      : "",
  ].filter(Boolean);

  const artifactRows = (detail.artifacts || []).map(
    (artifact) => `
      <article class="stack-card">
        <header>
          <strong>${escapeHtml(artifact.artifact_kind)}</strong>
          <span class="meta-pill">${escapeHtml(artifact.artifact_id)}</span>
        </header>
        <p>${escapeHtml(artifact.storage_path || "Payload-backed artifact")}</p>
        <div class="artifact-actions">
          ${downloadButton(
            "Open artifact",
            `/agent-tasks/${detail.task_id}/artifacts/${artifact.artifact_id}`,
            `${artifact.artifact_kind}.json`,
          )}
        </div>
      </article>
    `,
  );

  const verificationRows = (detail.verifications || []).map(
    (verification) => `
      <article class="stack-card">
        <header>
          <strong>${escapeHtml(verification.verifier_type)}</strong>
          <span class="status-pill ${escapeHtml(verification.outcome)}">${escapeHtml(formatStatusLabel(verification.outcome))}</span>
        </header>
        <p>${escapeHtml((verification.reasons || []).join(" · ") || "No reasons recorded.")}</p>
      </article>
    `,
  );

  const outcomeRows = (detail.outcomes || []).map(
    (outcome) => `
      <article class="stack-card">
        <header>
          <strong>${escapeHtml(outcome.outcome_label)}</strong>
          <span class="meta-pill">${escapeHtml(outcome.created_by)}</span>
        </header>
        <p>${escapeHtml(outcome.note || "No outcome note recorded.")}</p>
      </article>
    `,
  );

  const cards = [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(detail.task_type)}</strong>
          <span class="status-pill ${escapeHtml(detail.status)}">${escapeHtml(formatStatusLabel(detail.status))}</span>
        </header>
        <div class="status-meta">
          <span>${escapeHtml(detail.workflow_version)}</span>
          <span>${escapeHtml(detail.side_effect_level)}</span>
          <span>${detail.requires_approval ? "approval required" : "auto-run"}</span>
          <span>attempts ${formatInteger(detail.attempts)}</span>
        </div>
        <p>${escapeHtml(detail.error_message || detail.approval_note || detail.rejection_note || "No current task error, approval note, or rejection note recorded.")}</p>
        <div class="artifact-actions">${artifactButtons.join("")}</div>
      </article>
    `,
    jsonCard("Task input", detail.input),
    jsonCard("Task result", detail.result, "No structured result is persisted yet."),
    detail.artifacts?.length ? artifactRows.join("") : `<article class="stack-card"><strong>Artifacts</strong><p>No task artifacts recorded.</p></article>`,
    detail.verifications?.length ? verificationRows.join("") : `<article class="stack-card"><strong>Verifications</strong><p>No verifier rows recorded.</p></article>`,
    detail.outcomes?.length ? outcomeRows.join("") : `<article class="stack-card"><strong>Outcome labels</strong><p>No operator outcomes recorded.</p></article>`,
  ];

  renderStackCards(container, cards);
}

function renderTaskContext(detailState, contextState) {
  const container = byId("agent-task-context");
  if (!container) {
    return;
  }
  if (detailState.error) {
    renderEmpty(container, formatApiError(detailState.error, "Unable to load task context."));
    return;
  }
  const detail = detailState.data;
  const context = contextState.data;
  if (!detail) {
    renderEmpty(container, "Select a task to inspect typed context and verifier state.");
    return;
  }

  const refCards = (context?.refs || detail.context_refs || []).map((ref) => {
    const links = [];
    if (ref.task_id) {
      links.push(
        internalLink(`/ui/agents.html?task_id=${encodeURIComponent(ref.task_id)}`, "Open task"),
      );
    }
    if (ref.replay_run_id) {
      links.push(
        internalLink(
          `/ui/search.html?replay_run_id=${encodeURIComponent(ref.replay_run_id)}`,
          "Open replay run",
        ),
      );
    }
    if (ref.artifact_id) {
      links.push(
        downloadButton(
          "Open artifact",
          `/agent-tasks/${encodeURIComponent(ref.task_id || detail.task_id)}/artifacts/${encodeURIComponent(ref.artifact_id)}`,
          `${ref.ref_key || "artifact"}.json`,
        ),
      );
    }

    return `
      <article class="stack-card">
        <header>
          <strong>${escapeHtml(ref.ref_key)}</strong>
          <span class="meta-pill">${escapeHtml(ref.freshness_status || ref.ref_kind)}</span>
        </header>
        <p>${escapeHtml(ref.summary || "No ref summary recorded.")}</p>
        <div class="artifact-actions">${links.join("")}</div>
      </article>
    `;
  });

  const cards = [
    detail.context_summary
      ? `
        <article class="status-card">
          <header>
            <strong>${escapeHtml(detail.context_summary.headline || "Context summary")}</strong>
            <span class="meta-pill">${escapeHtml(detail.context_freshness_status || "unknown")}</span>
          </header>
          <p>${escapeHtml(detail.context_summary.goal || detail.context_summary.decision || "No context goal or decision recorded.")}</p>
          <p>${escapeHtml(detail.context_summary.next_action || "No next action recorded.")}</p>
        </article>
      `
      : `<article class="stack-card"><strong>Context summary</strong><p>No context summary recorded.</p></article>`,
    contextState.error
      ? `
        <article class="stack-card">
          <header>
            <strong>Context output</strong>
            <span class="status-pill failed">unavailable</span>
          </header>
          <p>${escapeHtml(formatApiError(contextState.error, "Unable to load task context output."))}</p>
        </article>
      `
      : "",
    context ? jsonCard("Context output", context.output, "No typed context output recorded.") : "",
    ...refCards,
  ].filter(Boolean);

  renderStackCards(container, cards);
}

function renderAgentTaskCollections() {
  const activeContainer = byId("active-agent-tasks");
  const recentContainer = byId("agent-task-list");

  if (uiState.agents.activeTasksError) {
    renderEmpty(
      activeContainer,
      formatApiError(uiState.agents.activeTasksError, "Unable to load active agent tasks."),
    );
  } else {
    renderActiveTasks(activeContainer, uiState.agents.activeTasks || []);
  }

  if (uiState.agents.recentTasksError) {
    renderEmpty(
      recentContainer,
      formatApiError(uiState.agents.recentTasksError, "Unable to load recent task records."),
    );
    return;
  }
  renderActiveTasks(recentContainer, uiState.agents.recentTasks || []);
}

async function refreshAgentTaskCollections() {
  const activeStatuses = ["processing", "queued", "retry_wait", "blocked", "awaiting_approval"]
    .map((status) => `status=${encodeURIComponent(status)}`)
    .join("&");
  const [activeTasksState, recentTasksState] = await Promise.all([
    fetchState(`/agent-tasks?${activeStatuses}&limit=24`),
    fetchState("/agent-tasks?limit=36"),
  ]);

  uiState.agents.activeTasks = activeTasksState.data || [];
  uiState.agents.recentTasks = recentTasksState.data || [];
  uiState.agents.activeTasksError = activeTasksState.error;
  uiState.agents.recentTasksError = recentTasksState.error;
  setText("agent-active-count", formatInteger(uiState.agents.activeTasks.length));

  renderAgentTaskCollections();
}

function updateAgentActionState(detail) {
  const approvalEnabled = detail?.status === "awaiting_approval";
  const outcomeEnabled = Boolean(detail?.task_id);

  const approveButton = byId("agent-approve");
  const rejectButton = byId("agent-reject");
  const outcomeButton = byId("agent-outcome-submit");
  if (approveButton) {
    approveButton.disabled = !approvalEnabled;
  }
  if (rejectButton) {
    rejectButton.disabled = !approvalEnabled;
  }
  if (outcomeButton) {
    outcomeButton.disabled = !outcomeEnabled;
  }

  if (!detail) {
    setNote("agent-action-note", "Select a task first. Approval actions only work for tasks waiting on approval.");
    return;
  }
  if (approvalEnabled) {
    setNote("agent-action-note", "The selected task is awaiting approval. Approval and rejection are enabled.");
    return;
  }
  setNote(
    "agent-action-note",
    "Approval actions are disabled because the selected task is not awaiting approval. Outcome labeling remains available.",
  );
}

async function loadSelectedTask(taskId) {
  if (!taskId) {
    renderTaskDetail({ data: null, error: null });
    renderTaskContext({ data: null, error: null }, { data: null, error: null });
    updateAgentActionState(null);
    return;
  }
  uiState.agents.selectedTaskId = String(taskId);
  setQueryParam("task_id", taskId);
  renderAgentTaskCollections();

  const [detailState, contextState] = await Promise.all([
    fetchState(`/agent-tasks/${taskId}`),
    fetchState(`/agent-tasks/${taskId}/context`),
  ]);
  renderTaskDetail(detailState);
  renderTaskContext(detailState, contextState);
  updateAgentActionState(detailState.data);
}

async function loadAgentsPage() {
  const activeStatuses = ["processing", "queued", "retry_wait", "blocked", "awaiting_approval"]
    .map((status) => `status=${encodeURIComponent(status)}`)
    .join("&");
  const [activeTasksState, recommendationSummaryState, decisionSignalsState, valueDensityState, harnessState, recentTasksState] =
    await Promise.all([
      fetchState(`/agent-tasks?${activeStatuses}&limit=24`),
      fetchState("/agent-tasks/analytics/recommendations"),
      fetchState("/agent-tasks/analytics/decision-signals"),
      fetchState("/agent-tasks/analytics/value-density"),
      getHarnessCatalogState(),
      fetchState("/agent-tasks?limit=36"),
    ]);
  const harnesses = harnessState.data || [];

  uiState.agents.activeTasks = activeTasksState.data || [];
  uiState.agents.recentTasks = recentTasksState.data || [];
  uiState.agents.activeTasksError = activeTasksState.error;
  uiState.agents.recentTasksError = recentTasksState.error;

  setText("agent-active-count", formatInteger(uiState.agents.activeTasks.length));
  setText(
    "agent-improvement-rate",
    recommendationSummaryState.data
      ? formatPercent(recommendationSummaryState.data.downstream_improvement_rate || 0)
      : "Locked",
  );
  setText("agent-signal-count", formatInteger(decisionSignalsState.data?.length || 0));

  renderAgentTaskCollections();
  renderDecisionSignals(byId("agent-decision-signals"), decisionSignalsState.data || []);

  const valueContainer = byId("agent-value-density");
  if (valueDensityState.error) {
    renderEmpty(
      valueContainer,
      formatApiError(valueDensityState.error, "Unable to load workflow value density."),
    );
  } else {
    renderStackCards(
      valueContainer,
      (valueDensityState.data || []).map(
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

  if (harnessState.error) {
    renderEmpty(
      byId("agent-harnesses"),
      formatApiError(harnessState.error, "Unable to load harness registry."),
    );
  } else {
    renderHarnessCards(byId("agent-harnesses"), harnesses, false);
  }

  const initialTaskId =
    uiState.agents.selectedTaskId ||
    uiState.agents.activeTasks?.[0]?.task_id ||
    uiState.agents.recentTasks?.[0]?.task_id ||
    null;
  await loadSelectedTask(initialTaskId);

  byId("agent-approval-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const taskId = uiState.agents.selectedTaskId;
    if (!taskId) {
      setNote("agent-action-note", "Select a task first.", true);
      return;
    }
    const payload = {
      approved_by: byId("agent-approval-actor")?.value || "",
      approval_note: byId("agent-approval-note")?.value || null,
    };
    const state = await fetchState(`/agent-tasks/${taskId}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (state.error) {
      setNote("agent-action-note", formatApiError(state.error, "Approval failed."), true);
      return;
    }
    setNote("agent-action-note", "Task approved.");
    await refreshAgentTaskCollections();
    await loadSelectedTask(taskId);
  });

  byId("agent-rejection-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const taskId = uiState.agents.selectedTaskId;
    if (!taskId) {
      setNote("agent-action-note", "Select a task first.", true);
      return;
    }
    const payload = {
      rejected_by: byId("agent-rejection-actor")?.value || "",
      rejection_note: byId("agent-rejection-note")?.value || null,
    };
    const state = await fetchState(`/agent-tasks/${taskId}/reject`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (state.error) {
      setNote("agent-action-note", formatApiError(state.error, "Rejection failed."), true);
      return;
    }
    setNote("agent-action-note", "Task rejected.");
    await refreshAgentTaskCollections();
    await loadSelectedTask(taskId);
  });

  byId("agent-outcome-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const taskId = uiState.agents.selectedTaskId;
    if (!taskId) {
      setNote("agent-action-note", "Select a task first.", true);
      return;
    }
    const payload = {
      outcome_label: byId("agent-outcome-label")?.value || "useful",
      created_by: byId("agent-outcome-actor")?.value || "",
      note: byId("agent-outcome-note")?.value || null,
    };
    const state = await fetchState(`/agent-tasks/${taskId}/outcomes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (state.error) {
      setNote("agent-action-note", formatApiError(state.error, "Outcome labeling failed."), true);
      return;
    }
    setNote("agent-action-note", "Outcome label attached.");
    await refreshAgentTaskCollections();
    await loadSelectedTask(taskId);
  });
}

function bindGlobalActionDelegation() {
  document.addEventListener("click", async (event) => {
    const target =
      event.target instanceof Element ? event.target : event.target?.parentElement || null;
    const trigger = target?.closest("[data-ui-action]");
    if (!trigger) {
      return;
    }

    const action = trigger.dataset.uiAction;
    if (action === "download") {
      event.preventDefault();
      try {
        await downloadProtectedResource(
          trigger.dataset.downloadPath,
          trigger.dataset.downloadName || "download",
        );
      } catch (error) {
        window.alert(formatApiError(error, "Download failed."));
      }
      return;
    }

    if (action === "select-document") {
      event.preventDefault();
      await loadSelectedDocument(trigger.dataset.documentId);
      return;
    }

    if (action === "load-replay-run") {
      event.preventDefault();
      await loadReplayRunDetail(trigger.dataset.replayRunId);
      return;
    }

    if (action === "load-harness-evaluation") {
      event.preventDefault();
      await loadHarnessEvaluationDetail(trigger.dataset.harnessEvaluationId);
      return;
    }

    if (action === "replay-selected-request") {
      event.preventDefault();
      await replaySelectedSearchRequest();
      return;
    }

    if (action === "select-task") {
      event.preventDefault();
      await loadSelectedTask(trigger.dataset.taskId);
      return;
    }
  });
}

async function init() {
  bindGlobalActionDelegation();
  const context = await loadGlobalChrome();
  renderAuthControls(context);

  if (page === "landing") {
    await loadLandingPage(context);
    return;
  }
  if (page === "documents") {
    await loadDocumentsPage(context);
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
