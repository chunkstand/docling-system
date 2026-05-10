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
    contextPack:
      result.context_pack ||
      output.context_pack ||
      result.harness?.document_generation_context_pack ||
      output.harness?.document_generation_context_pack ||
      null,
    contextPackEvaluation: result.evaluation || output.evaluation || null,
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
            label: "context pack",
            state: actionsByType.has("evaluate_document_generation_context_pack")
              ? "passed"
              : "failed",
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

function syncClaimSupportReplayControls() {
  const staleInput = byId("claim-support-replay-stale-hours");
  const includeClosedSelect = byId("claim-support-replay-include-closed");
  if (staleInput) {
    staleInput.value = String(uiState.agents.claimSupportReplayStaleHours || 24);
  }
  if (includeClosedSelect) {
    includeClosedSelect.value = uiState.agents.claimSupportReplayIncludeClosed
      ? "all"
      : "open";
  }
}

function claimSupportReplayControls() {
  const staleInput = byId("claim-support-replay-stale-hours");
  const includeClosedSelect = byId("claim-support-replay-include-closed");
  const staleValue = Number(staleInput?.value || uiState.agents.claimSupportReplayStaleHours || 24);
  return {
    staleAfterHours: Math.min(720, Math.max(1, Number.isFinite(staleValue) ? staleValue : 24)),
    includeClosed:
      (includeClosedSelect?.value || (uiState.agents.claimSupportReplayIncludeClosed ? "all" : "open")) ===
      "all",
  };
}

function claimSupportReplayActor() {
  return byId("claim-support-replay-actor")?.value?.trim() || "docling-system";
}

function claimSupportReplayWorklistPath() {
  const controls = claimSupportReplayControls();
  uiState.agents.claimSupportReplayStaleHours = controls.staleAfterHours;
  uiState.agents.claimSupportReplayIncludeClosed = controls.includeClosed;
  const params = new URLSearchParams({
    stale_after_hours: String(controls.staleAfterHours),
    limit: "12",
  });
  if (controls.includeClosed) {
    params.set("include_closed", "true");
  }
  return `/agent-tasks/claim-support-policy-change-impacts/worklist?${params.toString()}`;
}

function updateClaimSupportReplayQueryParams() {
  setQueryParam(
    "claim_support_replay_stale_after_hours",
    String(uiState.agents.claimSupportReplayStaleHours || 24),
  );
  setQueryParam(
    "claim_support_replay_include_closed",
    uiState.agents.claimSupportReplayIncludeClosed ? "true" : null,
  );
}

function renderClaimSupportReplaySummary(worklist) {
  const container = byId("claim-support-replay-summary");
  if (!container) {
    return;
  }
  const summary = worklist?.summary;
  if (!summary) {
    renderEmpty(container, "Replay impact summary is unavailable.");
    return;
  }
  const statusCounts = summary.replay_status_counts || {};
  container.className = "mini-grid";
  container.innerHTML = [
    {
      label: "Open impacts",
      value: summary.open_count || 0,
      detail: `${formatInteger(summary.total_count || 0)} total policy impacts`,
    },
    {
      label: "Stale open impacts",
      value: summary.stale_open_count || 0,
      detail: `${formatInteger(summary.stale_after_hours || 24)} hour threshold`,
    },
    {
      label: "Blocked impacts",
      value: statusCounts.blocked || 0,
      detail: `${formatInteger(statusCounts.queued || 0)} queued · ${formatInteger(statusCounts.pending || 0)} pending`,
    },
    {
      label: "Listed rows",
      value: worklist.item_count || 0,
      detail: `${formatInteger(worklist.matching_count || worklist.item_count || 0)} matching · generated ${formatDateTime(worklist.generated_at)}`,
    },
  ]
    .map(
      (row) => `
        <article class="summary-card">
          <span>${escapeHtml(row.label)}</span>
          <strong>${formatInteger(row.value)}</strong>
          <p>${escapeHtml(row.detail)}</p>
        </article>
      `,
    )
    .join("");
}

function claimSupportReplayTaskLabel(task) {
  const label = TECHNICAL_REPORT_TASK_LABELS[task.task_type] || task.task_type;
  const required = task.is_required_for_closure ? " required" : "";
  return `${label}: ${formatStatusLabel(task.status)}${required}`;
}

function renderClaimSupportReplayWorkbench(state) {
  const worklistContainer = byId("claim-support-replay-worklist");
  if (!worklistContainer) {
    return;
  }
  if (state.error) {
    const message = formatApiError(state.error, "Unable to load claim-support replay worklist.");
    renderEmpty(byId("claim-support-replay-summary"), message);
    renderEmpty(worklistContainer, message);
    setNote("claim-support-replay-note", message, true);
    return;
  }
  const worklist = state.data;
  uiState.agents.claimSupportReplayWorklist = worklist || null;
  uiState.agents.claimSupportReplayWorklistError = null;
  renderClaimSupportReplaySummary(worklist);
  setNote(
    "claim-support-replay-note",
    worklist
      ? `${formatInteger(worklist.item_count || 0)} of ${formatInteger(worklist.matching_count || worklist.item_count || 0)} replay impact rows loaded.`
      : "Replay impact rows are unavailable.",
    !worklist,
  );
  if (!worklist?.items?.length) {
    renderStackCards(worklistContainer, [
      `
        <article class="status-card">
          <header>
            <strong>No replay impacts in scope</strong>
            <span class="status-pill completed">clear</span>
          </header>
          <p>The current policy-change replay ledger has no rows in the selected scope.</p>
        </article>
      `,
    ]);
    return;
  }

  renderStackCards(
    worklistContainer,
    worklist.items.map((item) => {
      const impact = item.change_impact || {};
      const links = item.operator_links || {};
      const changeImpactId = impact.change_impact_id;
      const auditButtons = (item.audit_bundle_task_ids || [])
        .slice(0, 4)
        .map((taskId) =>
          downloadButton(
            `Audit ${shortId(taskId)}`,
            `/agent-tasks/${encodeURIComponent(taskId)}/audit-bundle`,
            `${taskId}-audit-bundle.json`,
          ),
        )
        .join("");
      const replayTaskButtons = (item.replay_tasks || [])
        .slice(0, 6)
        .map(
          (task) => `
            <button
              type="button"
              class="secondary-link button-link secondary-button compact-button"
              data-ui-action="select-task"
              data-task-id="${escapeHtml(task.task_id)}"
            >
              ${escapeHtml(claimSupportReplayTaskLabel(task))}
            </button>
          `,
        )
        .join("");
      const actionButtons = [
        item.recommended_action === "queue_replay"
          ? `
            <button
              type="button"
              class="button-link compact-button"
              data-ui-action="queue-claim-support-replay"
              data-change-impact-id="${escapeHtml(changeImpactId)}"
            >
              Queue replay
            </button>
          `
          : "",
        item.is_open
          ? `
            <button
              type="button"
              class="secondary-link button-link secondary-button compact-button"
              data-ui-action="refresh-claim-support-replay-status"
              data-change-impact-id="${escapeHtml(changeImpactId)}"
            >
              Refresh status
            </button>
          `
          : "",
        links.detail
          ? downloadButton("Impact JSON", links.detail, `${changeImpactId}-impact.json`)
          : "",
        links.closure_artifact
          ? downloadButton(
              "Closure receipt",
              links.closure_artifact,
              `${changeImpactId}-replay-closure.json`,
            )
          : "",
      ].join("");
      const reasons = compactList(item.reasons || [], 5);
      const taskSummary = compactList(
        (item.replay_tasks || []).map((task) => claimSupportReplayTaskLabel(task)),
        5,
      );
      return `
        <article class="status-card replay-impact-card">
          <header>
            <strong>${escapeHtml(impact.policy_name || "claim-support policy")} ${escapeHtml(impact.policy_version || "")}</strong>
            <span class="status-pill ${escapeHtml(item.severity)}">${escapeHtml(item.status_label || item.severity)}</span>
          </header>
          <div class="status-meta">
            <span>${formatInteger(impact.affected_generated_document_count || 0)} report docs</span>
            <span>${formatInteger(impact.affected_verification_count || 0)} verifier rows</span>
            <span>${formatInteger(impact.replay_recommended_count || 0)} replay recommendations</span>
            <span>${formatDecimal(item.status_age_hours || 0, 1)}h since status update</span>
          </div>
          <p>${escapeHtml(item.next_action || "Inspect replay impact row.")}</p>
          <p>${escapeHtml(reasons)}</p>
          <p>${escapeHtml(taskSummary)}</p>
          <div class="artifact-actions">${actionButtons}${auditButtons}${replayTaskButtons}</div>
        </article>
      `;
    }),
  );
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

async function refreshClaimSupportReplayWorkbench({ announce = false } = {}) {
  const state = await fetchState(claimSupportReplayWorklistPath());
  uiState.agents.claimSupportReplayWorklist = state.data || null;
  uiState.agents.claimSupportReplayWorklistError = state.error;
  renderClaimSupportReplayWorkbench(state);
  updateClaimSupportReplayQueryParams();
  if (announce && !state.error) {
    recordActivity(
      "Claim-support replay worklist refreshed",
      `${formatInteger(state.data?.item_count || 0)} of ${formatInteger(state.data?.matching_count || state.data?.item_count || 0)} replay impact rows loaded.`,
      "success",
    );
  }
  if (state.error) {
    recordActivity(
      "Claim-support replay worklist unavailable",
      formatApiError(state.error, "Unable to load claim-support replay worklist."),
      "error",
    );
  }
}

async function queueClaimSupportReplay(changeImpactId) {
  const state = await fetchState(
    `/agent-tasks/claim-support-policy-change-impacts/${encodeURIComponent(changeImpactId)}/replay-tasks`,
    {
      method: "POST",
      body: JSON.stringify({ requested_by: claimSupportReplayActor() }),
    },
  );
  if (state.error) {
    const message = formatApiError(state.error, "Queueing replay tasks failed.");
    setNote("claim-support-replay-note", message, true);
    recordActivity("Replay queue failed", message, "error");
    return;
  }
  setNote("claim-support-replay-note", "Replay tasks queued.");
  recordActivity(
    "Claim-support replay queued",
    `${formatInteger(state.data?.replay_task_ids?.length || 0)} replay tasks linked to impact ${shortId(changeImpactId)}.`,
    "success",
  );
  await Promise.all([
    refreshClaimSupportReplayWorkbench(),
    refreshAgentTaskCollections(),
    refreshAgentDecisionSignals(),
  ]);
}

async function refreshClaimSupportReplayStatus(changeImpactId) {
  const state = await fetchState(
    `/agent-tasks/claim-support-policy-change-impacts/${encodeURIComponent(changeImpactId)}/replay-status`,
    { method: "POST" },
  );
  if (state.error) {
    const message = formatApiError(state.error, "Replay status refresh failed.");
    setNote("claim-support-replay-note", message, true);
    recordActivity("Replay status refresh failed", message, "error");
    return;
  }
  setNote(
    "claim-support-replay-note",
    `Replay status is ${formatStatusLabel(state.data?.replay_status)}.`,
  );
  recordActivity(
    "Claim-support replay status refreshed",
    `Impact ${shortId(changeImpactId)} is ${formatStatusLabel(state.data?.replay_status)}.`,
    state.data?.replay_status === "blocked" ? "error" : "success",
  );
  await Promise.all([
    refreshClaimSupportReplayWorkbench(),
    refreshAgentTaskCollections(),
    refreshAgentDecisionSignals(),
  ]);
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
  const contextPack = payload.contextPack;
  const contextPackEvaluation = payload.contextPackEvaluation;
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
  const successMetrics =
    contextPackEvaluation?.success_metrics ||
    contextPack?.success_metrics ||
    harness?.success_metrics ||
    draft?.success_metrics ||
    detail.result?.success_metrics ||
    [];
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
    contextPack
      ? `
        <article class="stack-card">
          <header>
            <strong>Generation context pack</strong>
            <span class="meta-pill">${escapeHtml(contextPackEvaluation?.gate_outcome || "packaged")}</span>
          </header>
          <div class="status-meta">
            <span>${formatInteger(contextPack.claim_contract?.length || 0)} claims</span>
            <span>${formatInteger(contextPack.evidence_cards?.length || 0)} cards</span>
            <span>${formatInteger(contextPack.search_evidence_package_exports?.length || 0)} source packages</span>
            <span>${formatInteger(contextPackEvaluation?.summary?.failed_check_count || 0)} failed checks</span>
          </div>
          <p>${escapeHtml(contextPack.context_pack_sha256 || "No context-pack hash recorded.")}</p>
        </article>
      `
      : "",
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

