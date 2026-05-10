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
  "evaluate_document_generation_context_pack",
  "draft_technical_report",
  "verify_technical_report",
];
const TECHNICAL_REPORT_TASK_LABELS = {
  plan_technical_report: "Plan",
  build_report_evidence_cards: "Evidence cards",
  prepare_report_agent_harness: "Agent harness",
  evaluate_document_generation_context_pack: "Context pack eval",
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
    claimSupportReplayStaleHours: Number(
      queryParams.get("claim_support_replay_stale_after_hours") || 24,
    ),
    claimSupportReplayIncludeClosed:
      queryParams.get("claim_support_replay_include_closed") === "true",
    claimSupportReplayWorklist: null,
    claimSupportReplayWorklistError: null,
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

