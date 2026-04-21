const page = document.body.dataset.page;
const queryParams = new URLSearchParams(window.location.search);

const UI_AUTH_STORAGE_KEY = "docling-system-ui-auth-v1";
const DEFAULT_FETCH_TIMEOUT_MS = 30000;
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
const TECHNICAL_REPORT_TASK_TYPES = [
  "plan_technical_report",
  "build_report_evidence_cards",
  "prepare_report_agent_harness",
  "draft_technical_report",
  "verify_technical_report",
];
const TECHNICAL_REPORT_TASK_LABELS = {
  plan_technical_report: "Plan",
  build_report_evidence_cards: "Evidence cards",
  prepare_report_agent_harness: "Agent harness",
  draft_technical_report: "Draft",
  verify_technical_report: "Verification gate",
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
  activity: [],
  documents: {
    rows: [],
    totalCount: 0,
    selectedDocumentId: queryParams.get("document_id"),
    filter: "",
    outputsByDocumentId: new Map(),
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
    reportTasks: [],
    activeTasksError: null,
    recentTasksError: null,
    reportTasksError: null,
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

function formatSignedInteger(value) {
  const number = Number(value || 0);
  const prefix = number > 0 ? "+" : "";
  return `${prefix}${formatInteger(number)}`;
}

function formatSignedDecimal(value, digits = 3) {
  const number = Number(value || 0);
  const prefix = number > 0 ? "+" : "";
  return `${prefix}${formatDecimal(number, digits)}`;
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

function shortId(value) {
  const raw = String(value || "");
  return raw.length > 8 ? raw.slice(0, 8) : raw || "unknown";
}

function describeDocumentSelection(documentId) {
  const match = uiState.documents.rows.find((row) => String(row.document_id) === String(documentId));
  return match?.title || match?.source_filename || `document ${shortId(documentId)}`;
}

function describeTaskSelection(taskId) {
  const rows = [...(uiState.agents.activeTasks || []), ...(uiState.agents.recentTasks || [])];
  const match = rows.find((row) => String(row.task_id) === String(taskId));
  return match?.task_type || `task ${shortId(taskId)}`;
}

function isTechnicalReportTask(taskType) {
  return TECHNICAL_REPORT_TASK_TYPES.includes(String(taskType || ""));
}

function initTabs() {
  document.querySelectorAll("[data-tab-group]").forEach((group) => {
    if (group.dataset.tabsBound === "true") {
      return;
    }
    const groupName = group.dataset.tabGroup;
    const buttons = Array.from(group.querySelectorAll("[data-tab-button]"));
    const panels = Array.from(group.querySelectorAll(`[data-tab-panel="${groupName}"]`));
    const setActiveTab = (tabId) => {
      buttons.forEach((button) => {
        const isActive = button.dataset.tabButton === tabId;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("role", "tab");
        button.setAttribute("aria-selected", isActive ? "true" : "false");
        button.tabIndex = isActive ? 0 : -1;
      });
      panels.forEach((panel) => {
        panel.setAttribute("role", "tabpanel");
        panel.hidden = panel.id !== tabId;
      });
    };

    const defaultTab = group.dataset.defaultTab || buttons[0]?.dataset.tabButton || "";
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        setActiveTab(button.dataset.tabButton);
        handleTabActivated(button.dataset.tabButton);
      });
    });
    setActiveTab(defaultTab);
    group.dataset.tabsBound = "true";
  });
}

function handleTabActivated(tabId) {
  if (tabId === "documents-outputs" && uiState.documents.selectedDocumentId) {
    void loadDocumentOutputs(uiState.documents.selectedDocumentId);
  }
}

function renderActivityFeed() {
  const container = byId("page-activity-feed");
  if (!container) {
    return;
  }
  if (!uiState.activity.length) {
    renderEmpty(container, "Runtime actions will appear here.");
    return;
  }
  container.className = "activity-feed";
  container.innerHTML = uiState.activity
    .map(
      (entry) => `
        <article class="activity-item ${escapeHtml(entry.tone)}">
          <div class="activity-dot"></div>
          <div class="activity-copy">
            <header>
              <strong>${escapeHtml(entry.title)}</strong>
              <span>${escapeHtml(formatDateTime(entry.createdAt))}</span>
            </header>
            <p>${escapeHtml(entry.detail)}</p>
          </div>
        </article>
      `,
    )
    .join("");
}

function recordActivity(title, detail, tone = "info") {
  uiState.activity = [
    {
      title: String(title || "Activity"),
      detail: String(detail || ""),
      tone: tone === "error" ? "error" : tone === "success" ? "success" : "info",
      createdAt: new Date().toISOString(),
    },
    ...uiState.activity,
  ].slice(0, 12);
  renderActivityFeed();
}

function renderCheckStrip(items) {
  const rows = (items || []).filter(Boolean);
  if (!rows.length) {
    return "";
  }
  return `
    <div class="check-strip">
      ${rows
        .map(
          (item) => `
            <span class="check-chip ${escapeHtml(item.state || "neutral")}">${escapeHtml(item.label)}</span>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderTimeline(items) {
  const rows = (items || []).filter((item) => item?.time);
  if (!rows.length) {
    return "";
  }
  return `
    <ul class="timeline-list">
      ${rows
        .map(
          (item) => `
            <li>
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(formatDateTime(item.time))}</strong>
            </li>
          `,
        )
        .join("")}
    </ul>
  `;
}

function renderMetricComparison(label, baselineValue, candidateValue, { digits = 0, preferLower = false } = {}) {
  const baseline = Number(baselineValue || 0);
  const candidate = Number(candidateValue || 0);
  const delta = candidate - baseline;
  let state = "neutral";
  if (delta !== 0) {
    const improved = preferLower ? delta < 0 : delta > 0;
    state = improved ? "positive" : "negative";
  }
  const formatter = digits > 0 ? (value) => formatDecimal(value, digits) : (value) => formatInteger(value);
  const deltaLabel = digits > 0 ? formatSignedDecimal(delta, digits) : formatSignedInteger(delta);
  return `
    <article class="metric-compare">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(formatter(candidate))}</strong>
      <div class="metric-compare-meta">
        <span>baseline ${escapeHtml(formatter(baseline))}</span>
        <span class="delta-pill ${state}">${escapeHtml(deltaLabel)}</span>
      </div>
    </article>
  `;
}

function renderAcceptanceChecks(checks) {
  const rows = Object.entries(checks || {});
  if (!rows.length) {
    return `<p class="body-copy">No acceptance checks were persisted for this comparison.</p>`;
  }
  return `
    <div class="check-grid">
      ${rows
        .map(([name, value]) => {
          const passed = typeof value === "boolean" ? value : Boolean(value?.passed);
          return `
            <span class="check-chip ${passed ? "passed" : "failed"}">${escapeHtml(
              name.replaceAll("_", " "),
            )}</span>
          `;
        })
        .join("")}
    </div>
  `;
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
  const { timeoutMs = DEFAULT_FETCH_TIMEOUT_MS, signal, ...fetchOptions } = options;
  const headers = new Headers(options.headers || {});
  const authHeaders = buildAuthHeaders();
  for (const [name, value] of Object.entries(authHeaders)) {
    headers.set(name, value);
  }

  if (!(fetchOptions.body instanceof FormData) && fetchOptions.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const controller = new AbortController();
  const abortFromSignal = () => controller.abort();
  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener("abort", abortFromSignal, { once: true });
    }
  }
  const timeoutId =
    timeoutMs && timeoutMs > 0
      ? window.setTimeout(() => controller.abort(), timeoutMs)
      : null;

  let response;
  try {
    response = await fetch(url, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new ApiError("Request timed out.", {
        status: 0,
        code: "request_timeout",
      });
    }
    throw error;
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
    if (signal) {
      signal.removeEventListener("abort", abortFromSignal);
    }
  }

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
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), DEFAULT_FETCH_TIMEOUT_MS);
  let response;
  try {
    response = await fetch(path, { headers, signal: controller.signal });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new ApiError("Download timed out.", {
        status: 0,
        code: "request_timeout",
      });
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
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
  const scoreItems = [
    `overall ${formatDecimal(result.score, 3)}`,
    result.scores?.hybrid_score != null ? `hybrid ${formatDecimal(result.scores.hybrid_score, 3)}` : "",
    result.scores?.keyword_score != null ? `keyword ${formatDecimal(result.scores.keyword_score, 3)}` : "",
    result.scores?.semantic_score != null ? `semantic ${formatDecimal(result.scores.semantic_score, 3)}` : "",
  ].filter(Boolean);
  const rankMeta = logged && result.rank ? `<span>rank ${formatInteger(result.rank)}</span>` : "";
  const docLink = internalLink(
    `/ui/documents.html?document_id=${encodeURIComponent(result.document_id)}`,
    "Open document",
  );
  const shapeMeta =
    result.result_type === "table" && result.row_count != null && result.col_count != null
      ? `<span>${formatInteger(result.row_count)} rows x ${formatInteger(result.col_count)} cols</span>`
      : `<span>${escapeHtml(result.result_type === "table" ? "structured evidence" : "prose evidence")}</span>`;

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
        ${shapeMeta}
      </div>
      <div class="score-strip">
        ${scoreItems.map((item) => `<span class="score-chip">${escapeHtml(item)}</span>`).join("")}
      </div>
      <div class="result-snippet ${result.result_type === "table" ? "is-tabular" : ""}">
        ${escapeHtml(body || "No evidence text recorded for this result.")}
      </div>
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
  const summaryContainer = byId("agent-task-detail");
  const ioContainer = byId("agent-task-io");
  const artifactsContainer = byId("agent-task-artifacts");
  const verificationsContainer = byId("agent-task-verifications");
  const outcomesContainer = byId("agent-task-outcomes");
  const contextSummaryContainer = byId("agent-task-context-summary");

  if (!summaryContainer) {
    return;
  }
  if (detailState.error) {
    const message = formatApiError(detailState.error, "Unable to load task detail.");
    renderEmpty(summaryContainer, message);
    renderEmpty(ioContainer, message);
    renderEmpty(artifactsContainer, message);
    renderEmpty(verificationsContainer, message);
    renderEmpty(outcomesContainer, message);
    renderEmpty(contextSummaryContainer, message);
    return;
  }
  const detail = detailState.data;
  if (!detail) {
    renderEmpty(summaryContainer, "Select a task to inspect its durable detail.");
    renderEmpty(ioContainer, "Structured task input and result will appear here.");
    renderEmpty(artifactsContainer, "Task artifacts will appear here.");
    renderEmpty(verificationsContainer, "Verifier rows will appear here.");
    renderEmpty(outcomesContainer, "Outcome labels will appear here.");
    renderEmpty(
      contextSummaryContainer,
      "Select a task to inspect its current stage, decision posture, and next operator action.",
    );
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

  const summaryCards = [
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
        ${renderCheckStrip([
          {
            label: detail.requires_approval ? "approval gated" : "auto-run",
            state: detail.requires_approval ? "warning" : "passed",
          },
          {
            label: `${formatInteger(detail.artifact_count)} artifacts`,
            state: detail.artifact_count ? "passed" : "neutral",
          },
          {
            label: `${formatInteger(detail.verification_count)} verifications`,
            state: detail.verification_count ? "passed" : "neutral",
          },
        ])}
        <div class="artifact-actions">${artifactButtons.join("")}</div>
      </article>
    `,
    `
      <article class="stack-card">
        <header>
          <strong>Readable task summary</strong>
          <span class="meta-pill">${escapeHtml(detail.status)}</span>
        </header>
        <p>${escapeHtml(
          detail.status === "awaiting_approval"
            ? "This task is blocked on a human approval decision."
            : detail.status === "processing"
              ? "This task is actively running inside the bounded agent workflow."
              : detail.status === "failed"
                ? "This task failed and should be inspected with its failure artifact and context."
                : "This task is recorded with durable workflow state and can be reviewed from its artifacts and context.",
        )}</p>
        <p>${escapeHtml(
          detail.context_summary?.next_action ||
            detail.context_summary?.decision ||
            "No next action is recorded in the task context summary.",
        )}</p>
      </article>
    `,
  ];

  const ioCards = [
    jsonCard("Task input", detail.input),
    jsonCard("Task result", detail.result, "No structured result is persisted yet."),
    jsonCard("Model settings", detail.model_settings, "No model settings are persisted for this task."),
  ];

  const summaryContextCards = [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(detail.task_type)}</strong>
          <span class="meta-pill">${escapeHtml(detail.context_freshness_status || "context unknown")}</span>
        </header>
        <div class="status-meta">
          <span>${detail.requires_approval ? "approval required" : "auto-run"}</span>
          <span>${formatInteger(detail.outcome_count)} outcomes</span>
          <span>${formatInteger(detail.dependency_task_ids?.length || 0)} dependencies</span>
        </div>
        <p>${escapeHtml(
          detail.context_summary?.headline ||
            detail.context_summary?.goal ||
            "No context summary headline is recorded for this task.",
        )}</p>
        <p>${escapeHtml(
          detail.context_summary?.next_action ||
            "No next action is recorded in the task context summary.",
        )}</p>
      </article>
    `,
  ];

  renderStackCards(summaryContainer, summaryCards);
  renderStackCards(ioContainer, ioCards);
  renderStackCards(
    artifactsContainer,
    detail.artifacts?.length
      ? artifactRows
      : [`<article class="stack-card"><strong>Artifacts</strong><p>No task artifacts recorded.</p></article>`],
  );
  renderStackCards(
    verificationsContainer,
    detail.verifications?.length
      ? verificationRows
      : [`<article class="stack-card"><strong>Verifications</strong><p>No verifier rows recorded.</p></article>`],
  );
  renderStackCards(
    outcomesContainer,
    detail.outcomes?.length
      ? outcomeRows
      : [`<article class="stack-card"><strong>Outcome labels</strong><p>No operator outcomes recorded.</p></article>`],
  );
  renderStackCards(contextSummaryContainer, summaryContextCards);
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

function compactList(values, limit = 6) {
  const rows = (values || []).filter(Boolean).map((value) => String(value));
  if (!rows.length) {
    return "none";
  }
  const shown = rows.slice(0, limit);
  const extra = rows.length - shown.length;
  return extra > 0 ? `${shown.join(", ")} +${formatInteger(extra)} more` : shown.join(", ");
}

function reportPayloadFromTask(detail, context) {
  const result = detail?.result || {};
  const output = context?.output || {};
  return {
    plan: result.plan || output.plan || null,
    evidenceBundle: result.evidence_bundle || output.evidence_bundle || null,
    harness: result.harness || output.harness || null,
    draft: result.draft || output.draft || null,
    verification: result.verification || output.verification || null,
    verificationSummary: result.summary || output.summary || null,
  };
}

function renderReportHarnessContract(actionsState, workflowVersionsState) {
  const container = byId("agent-report-harness-contract");
  if (!container) {
    return;
  }
  if (actionsState.error) {
    renderEmpty(container, formatApiError(actionsState.error, "Unable to load agent action registry."));
    return;
  }
  const actionsByType = new Map((actionsState.data || []).map((action) => [action.task_type, action]));
  const registeredCount = TECHNICAL_REPORT_TASK_TYPES.filter((taskType) => actionsByType.has(taskType)).length;
  const workflowCount = (workflowVersionsState.data || []).reduce(
    (sum, row) => sum + (row.task_count || 0),
    0,
  );
  const cards = [
    `
      <article class="status-card">
        <header>
          <strong>Technical report harness contract</strong>
          <span class="meta-pill">${formatInteger(registeredCount)} / ${formatInteger(TECHNICAL_REPORT_TASK_TYPES.length)} actions</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(workflowCount)} total agent tasks</span>
          <span>${formatInteger((workflowVersionsState.data || []).length)} workflow versions</span>
          <span>live action registry</span>
        </div>
        <p>Action registry returned the task definitions currently available to the worker.</p>
        ${renderCheckStrip([
          {
            label: "plan",
            state: actionsByType.has("plan_technical_report") ? "passed" : "failed",
          },
          {
            label: "evidence cards",
            state: actionsByType.has("build_report_evidence_cards") ? "passed" : "failed",
          },
          {
            label: "wake harness",
            state: actionsByType.has("prepare_report_agent_harness") ? "passed" : "failed",
          },
          {
            label: "draft",
            state: actionsByType.has("draft_technical_report") ? "passed" : "failed",
          },
          {
            label: "verify",
            state: actionsByType.has("verify_technical_report") ? "passed" : "failed",
          },
        ])}
      </article>
    `,
    ...TECHNICAL_REPORT_TASK_TYPES.map((taskType) => {
      const action = actionsByType.get(taskType);
      return `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(TECHNICAL_REPORT_TASK_LABELS[taskType])}</strong>
            <span class="status-pill ${action ? "completed" : "failed"}">${action ? "registered" : "missing"}</span>
          </header>
          <p>${escapeHtml(action?.description || "No action definition is registered for this step.")}</p>
          <div class="status-meta">
            <span>${escapeHtml(action?.side_effect_level || "not registered")}</span>
            <span>${action ? (action.requires_approval ? "approval required" : "auto-run") : "not registered"}</span>
            <span>${escapeHtml(action?.output_schema_name || "no output schema")}</span>
          </div>
        </article>
      `;
    }),
  ];
  renderStackCards(container, cards);
}

function renderReportHarnessRuns(tasksState) {
  const container = byId("agent-report-harness-runs");
  if (!container) {
    return;
  }
  if (tasksState.error) {
    renderEmpty(container, formatApiError(tasksState.error, "Unable to load technical report tasks."));
    return;
  }
  const reportTasks = (tasksState.data || []).filter((task) => isTechnicalReportTask(task.task_type));
  uiState.agents.reportTasks = reportTasks;
  uiState.agents.reportTasksError = null;
  if (!reportTasks.length) {
    renderStackCards(container, [
      `
        <article class="status-card">
          <header>
            <strong>No persisted report workflow runs</strong>
            <span class="meta-pill">registry only</span>
          </header>
          <p>The action registry is available, but this database has not recorded a technical report workflow run in the loaded task window.</p>
        </article>
      `,
    ]);
    return;
  }
  renderStackCards(
    container,
    reportTasks.slice(0, 10).map(
      (task) => `
        <button
          type="button"
          class="status-card selectable-card ${uiState.agents.selectedTaskId === String(task.task_id) ? "is-selected" : ""}"
          data-ui-action="select-task"
          data-task-id="${escapeHtml(task.task_id)}"
        >
          <header>
            <strong>${escapeHtml(TECHNICAL_REPORT_TASK_LABELS[task.task_type] || task.task_type)}</strong>
            <span class="status-pill ${escapeHtml(task.status)}">${escapeHtml(formatStatusLabel(task.status))}</span>
          </header>
          <div class="status-meta">
            <span>${escapeHtml(task.workflow_version)}</span>
            <span>${escapeHtml(formatShortDate(task.created_at))}</span>
            <span>${task.requires_approval ? "approval-gated" : "auto-run"}</span>
          </div>
          <p>${escapeHtml(task.task_type)} · ${escapeHtml(shortId(task.task_id))}</p>
        </button>
      `,
    ),
  );
}

function renderReportHarnessPacket(detailState, contextState) {
  const container = byId("agent-report-harness-packet");
  if (!container) {
    return;
  }
  if (detailState?.error) {
    renderEmpty(container, formatApiError(detailState.error, "Unable to load report task packet."));
    return;
  }
  const detail = detailState?.data;
  const context = contextState?.data;
  if (!detail) {
    renderEmpty(
      container,
      "No technical report task is selected or available in the loaded task window.",
    );
    return;
  }
  if (!isTechnicalReportTask(detail.task_type)) {
    return;
  }

  const payload = reportPayloadFromTask(detail, context);
  const harness = payload.harness;
  const draft = payload.draft;
  const verification = payload.verification || (detail.verifications || []).find(
    (row) => row.verifier_type === "technical_report_gate",
  );
  const verificationSummary = payload.verificationSummary || verification?.metrics || {};
  const evidenceBundle = payload.evidenceBundle;
  const evidenceCards =
    harness?.evidence_cards ||
    draft?.evidence_cards ||
    evidenceBundle?.evidence_cards ||
    [];
  const graphContext = harness?.graph_context || draft?.graph_context || evidenceBundle?.graph_context || [];
  const claimContract = harness?.claim_contract || evidenceBundle?.claim_evidence_map || [];
  const claims = draft?.claims || [];
  const adapterContract = harness?.llm_adapter_contract || draft?.llm_adapter_contract || {};
  const contextRefs =
    harness?.context_refs ||
    adapterContract.harness_context_refs ||
    context?.refs ||
    detail.context_refs ||
    [];
  const allowedTools = harness?.allowed_tools || [];
  const requiredSkills = harness?.required_skills || [];
  const blockedSteps = harness?.workflow_state?.blocked_steps || [];
  const successMetrics = harness?.success_metrics || draft?.success_metrics || detail.result?.success_metrics || [];
  const failedMetricCount = successMetrics.filter((row) => row.passed === false).length;

  const cards = [
    `
      <article class="status-card">
        <header>
          <strong>${escapeHtml(TECHNICAL_REPORT_TASK_LABELS[detail.task_type] || detail.task_type)}</strong>
          <span class="status-pill ${escapeHtml(detail.status)}">${escapeHtml(formatStatusLabel(detail.status))}</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(evidenceCards.length)} evidence cards</span>
          <span>${formatInteger(claimContract.length || claims.length)} claim bindings</span>
          <span>${formatInteger(graphContext.length)} graph edges</span>
          <span>${formatInteger(contextRefs.length)} context refs</span>
        </div>
        <p>${escapeHtml(context?.summary?.next_action || detail.context_summary?.next_action || "No next action is recorded for this report task.")}</p>
        ${renderCheckStrip([
          {
            label: "wake context",
            state: contextRefs.length ? "passed" : "failed",
          },
          {
            label: "blocked steps",
            state: blockedSteps.length ? "failed" : "passed",
          },
          {
            label: "evidence binding",
            state: evidenceCards.length ? "passed" : "warning",
          },
          {
            label: "metric failures",
            state: failedMetricCount ? "warning" : "passed",
          },
        ])}
      </article>
    `,
    `
      <article class="stack-card">
        <header>
          <strong>LLM adapter contract</strong>
          <span class="meta-pill">${escapeHtml(adapterContract.primary_context_schema || "not packaged")}</span>
        </header>
        <p>${escapeHtml(adapterContract.primary_context_ref || "No primary context ref is recorded on this task.")}</p>
        <div class="status-meta">
          <span>${formatInteger((adapterContract.allowed_tool_names || allowedTools).length)} tools</span>
          <span>${formatInteger((adapterContract.required_skill_names || requiredSkills).length)} skills</span>
          <span>${escapeHtml(adapterContract.required_output_schema || "no output schema")}</span>
        </div>
        <p>Tools: ${escapeHtml(compactList(adapterContract.allowed_tool_names || allowedTools.map((row) => row.tool_name)))}</p>
        <p>Skills: ${escapeHtml(compactList(adapterContract.required_skill_names || requiredSkills.map((row) => row.skill_name)))}</p>
      </article>
    `,
    `
      <article class="stack-card">
        <header>
          <strong>Verification gates</strong>
          <span class="meta-pill">${escapeHtml(verification?.outcome || "not run")}</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(verificationSummary.unsupported_claim_count || 0)} unsupported claims</span>
          <span>${formatInteger(verificationSummary.unresolved_evidence_card_ref_count || 0)} missing evidence refs</span>
          <span>${formatInteger(verificationSummary.unresolved_graph_edge_ref_count || 0)} missing graph refs</span>
          <span>${formatInteger(verificationSummary.missing_wake_context_count || 0)} missing wake contexts</span>
        </div>
        <p>${escapeHtml((verification?.reasons || []).join(" · ") || "No verifier reasons recorded for this packet.")}</p>
      </article>
    `,
    contextRefs.length
      ? `
        <article class="stack-card">
          <header>
            <strong>Wake-up context refs</strong>
            <span class="meta-pill">${formatInteger(contextRefs.length)} refs</span>
          </header>
          <p>${escapeHtml(compactList(contextRefs.map((ref) => `${ref.ref_key}:${ref.freshness_status || ref.ref_kind}`), 8))}</p>
        </article>
      `
      : "",
    evidenceCards.length
      ? `
        <article class="stack-card">
          <header>
            <strong>Evidence surface</strong>
            <span class="meta-pill">${formatInteger(evidenceCards.length)} cards</span>
          </header>
          <p>${escapeHtml(compactList(evidenceCards.map((card) => `${card.evidence_card_id}:${card.source_type || card.evidence_kind}`), 8))}</p>
        </article>
      `
      : "",
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
  recordActivity(
    "Loading task workspace",
    `Refreshing ${describeTaskSelection(taskId)}.`,
  );

  const [detailState, contextState] = await Promise.all([
    fetchState(`/agent-tasks/${taskId}`),
    fetchState(`/agent-tasks/${taskId}/context`),
  ]);
  renderTaskDetail(detailState);
  renderTaskContext(detailState, contextState);
  renderReportHarnessRuns({ data: uiState.agents.reportTasks, error: uiState.agents.reportTasksError });
  if (isTechnicalReportTask(detailState.data?.task_type)) {
    renderReportHarnessPacket(detailState, contextState);
  }
  updateAgentActionState(detailState.data);
  if (detailState.error) {
    recordActivity("Task load failed", formatApiError(detailState.error, "Unable to load task detail."), "error");
  } else {
    recordActivity(
      "Task workspace ready",
      `${detailState.data?.task_type || "Task"} loaded with ${formatInteger(detailState.data?.artifact_count || 0)} artifacts and ${formatInteger(detailState.data?.verification_count || 0)} verifications.`,
      "success",
    );
  }
}

async function loadAgentsPage() {
  const activeStatuses = ["processing", "queued", "retry_wait", "blocked", "awaiting_approval"]
    .map((status) => `status=${encodeURIComponent(status)}`)
    .join("&");
  const [
    activeTasksState,
    recommendationSummaryState,
    decisionSignalsState,
    valueDensityState,
    harnessState,
    recentTasksState,
    actionDefinitionsState,
    workflowVersionsState,
    reportTasksState,
  ] =
    await Promise.all([
      fetchState(`/agent-tasks?${activeStatuses}&limit=24`),
      fetchState("/agent-tasks/analytics/recommendations"),
      fetchState("/agent-tasks/analytics/decision-signals"),
      fetchState("/agent-tasks/analytics/value-density"),
      getHarnessCatalogState(),
      fetchState("/agent-tasks?limit=36"),
      fetchState("/agent-tasks/actions"),
      fetchState("/agent-tasks/analytics/workflow-versions"),
      fetchState("/agent-tasks?limit=120"),
    ]);
  const harnesses = harnessState.data || [];

  uiState.agents.activeTasks = activeTasksState.data || [];
  uiState.agents.recentTasks = recentTasksState.data || [];
  uiState.agents.activeTasksError = activeTasksState.error;
  uiState.agents.recentTasksError = recentTasksState.error;
  uiState.agents.reportTasks = (reportTasksState.data || []).filter((task) =>
    isTechnicalReportTask(task.task_type),
  );
  uiState.agents.reportTasksError = reportTasksState.error;

  setText("agent-active-count", formatInteger(uiState.agents.activeTasks.length));
  setText(
    "agent-improvement-rate",
    recommendationSummaryState.data
      ? formatPercent(recommendationSummaryState.data.downstream_improvement_rate || 0)
      : "Locked",
  );
  setText("agent-signal-count", formatInteger(decisionSignalsState.data?.length || 0));

  renderAgentTaskCollections();
  renderReportHarnessContract(actionDefinitionsState, workflowVersionsState);
  renderReportHarnessRuns({
    data: uiState.agents.reportTasks,
    error: uiState.agents.reportTasksError,
  });
  renderDecisionSignals(byId("agent-decision-signals"), decisionSignalsState.data || []);
  recordActivity(
    "Agent workspace ready",
    `Loaded ${formatInteger(uiState.agents.activeTasks.length)} active tasks and ${formatInteger(uiState.agents.recentTasks.length)} recent task records.`,
    "success",
  );

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
  const latestReportTaskId = uiState.agents.reportTasks?.[0]?.task_id;
  if (latestReportTaskId && latestReportTaskId !== initialTaskId) {
    const [reportDetailState, reportContextState] = await Promise.all([
      fetchState(`/agent-tasks/${latestReportTaskId}`),
      fetchState(`/agent-tasks/${latestReportTaskId}/context`),
    ]);
    renderReportHarnessPacket(reportDetailState, reportContextState);
  } else if (!latestReportTaskId) {
    renderReportHarnessPacket({ data: null, error: null }, { data: null, error: null });
  }
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
      recordActivity("Approval failed", formatApiError(state.error, "Approval failed."), "error");
      return;
    }
    setNote("agent-action-note", "Task approved.");
    recordActivity(
      "Task approved",
      `Approved ${describeTaskSelection(taskId)}.`,
      "success",
    );
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
      recordActivity("Rejection failed", formatApiError(state.error, "Rejection failed."), "error");
      return;
    }
    setNote("agent-action-note", "Task rejected.");
    recordActivity(
      "Task rejected",
      `Rejected ${describeTaskSelection(taskId)}.`,
      "success",
    );
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
      recordActivity("Outcome labeling failed", formatApiError(state.error, "Outcome labeling failed."), "error");
      return;
    }
    setNote("agent-action-note", "Outcome label attached.");
    recordActivity(
      "Outcome label recorded",
      `Attached ${payload.outcome_label} to ${describeTaskSelection(taskId)}.`,
      "success",
    );
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
  initTabs();
  renderActivityFeed();
  const context = await loadGlobalChrome();
  renderAuthControls(context);
  recordActivity(
    "UI connected",
    context.runtimeStatus
      ? `Connected to ${runtimeApiMode(context.runtimeStatus)} API at ${runtimeBindLabel(context.runtimeStatus)}.`
      : "Connected to the operator UI; runtime status is unavailable for the current credential.",
    context.runtimeStatus ? "success" : "info",
  );

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
