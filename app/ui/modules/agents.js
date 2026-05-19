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

async function refreshAgentDecisionSignals() {
  const state = await fetchState("/agent-tasks/analytics/decision-signals");
  if (state.error) {
    recordActivity(
      "Decision signals unavailable",
      formatApiError(state.error, "Unable to refresh decision signals."),
      "error",
    );
    return;
  }
  setText("agent-signal-count", formatInteger(state.data?.length || 0));
  renderDecisionSignals(byId("agent-decision-signals"), state.data || []);
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
  syncClaimSupportReplayControls();
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
    claimSupportReplayWorklistState,
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
      fetchState(claimSupportReplayWorklistPath()),
    ]);
  const harnesses = harnessState.data || [];

  uiState.agents.activeTasks = activeTasksState.data || [];
  uiState.agents.recentTasks = recentTasksState.data || [];
  uiState.agents.activeTasksError = activeTasksState.error;
  uiState.agents.recentTasksError = recentTasksState.error;
  uiState.agents.claimSupportReplayWorklist = claimSupportReplayWorklistState.data || null;
  uiState.agents.claimSupportReplayWorklistError = claimSupportReplayWorklistState.error;
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
  renderClaimSupportReplayWorkbench(claimSupportReplayWorklistState);
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

  byId("claim-support-replay-controls")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await refreshClaimSupportReplayWorkbench({ announce: true });
    await refreshAgentDecisionSignals();
  });

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
