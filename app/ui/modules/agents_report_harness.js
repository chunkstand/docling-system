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
