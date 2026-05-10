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

