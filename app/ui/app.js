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

    if (action === "queue-claim-support-replay") {
      event.preventDefault();
      await queueClaimSupportReplay(trigger.dataset.changeImpactId);
      return;
    }

    if (action === "refresh-claim-support-replay-status") {
      event.preventDefault();
      await refreshClaimSupportReplayStatus(trigger.dataset.changeImpactId);
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
  if (page === "semantics") {
    await loadSemanticsPage(context);
    return;
  }
  if (page === "agents") {
    await loadAgentsPage();
  }
}

void init();
