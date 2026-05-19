const page = document.body.dataset.page;
const queryParams = new URLSearchParams(window.location.search);

const DEFAULT_HARNESS_NAME = "default_v1";
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

function compactList(values, limit = 6) {
  const rows = (values || []).filter(Boolean).map((value) => String(value));
  if (!rows.length) {
    return "none";
  }
  const shown = rows.slice(0, limit);
  const extra = rows.length - shown.length;
  return extra > 0 ? `${shown.join(", ")} +${formatInteger(extra)} more` : shown.join(", ");
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
