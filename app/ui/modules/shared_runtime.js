const UI_AUTH_STORAGE_KEY = "docling-system-ui-auth-v1";
const DEFAULT_FETCH_TIMEOUT_MS = 30000;

class ApiError extends Error {
  constructor(message, { status = 0, code = null, context = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.context = context;
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
