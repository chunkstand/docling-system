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
