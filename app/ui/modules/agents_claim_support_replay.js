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
