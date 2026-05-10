function renderSemanticBackfillStatus(statusState) {
  const summaryContainer = byId("semantic-backfill-summary");
  const missingContainer = byId("semantic-missing-documents");
  if (!summaryContainer) {
    return;
  }
  if (statusState.error) {
    const message = formatApiError(statusState.error, "Unable to load semantic backfill status.");
    renderEmpty(summaryContainer, message);
    renderEmpty(missingContainer, message);
    return;
  }
  const status = statusState.data;
  if (!status) {
    renderEmpty(summaryContainer, "Semantic backfill status is unavailable.");
    renderEmpty(missingContainer, "Missing-document sample is unavailable.");
    return;
  }

  const registry = status.current_registry || {};
  const graph = status.graph || {};
  const readiness = status.readiness || {};
  const activeDocs = Number(status.active_document_count || 0);
  const currentPasses = Number(status.active_current_pass_count || 0);
  const missingPasses = Number(status.missing_current_pass_count || 0);

  setText(
    "semantic-pass-coverage",
    `${formatInteger(currentPasses)} / ${formatInteger(activeDocs)}`,
  );
  setText("semantic-assertion-count", formatInteger(status.assertion_count || 0));
  setText("semantic-fact-count", formatInteger(status.fact_count || 0));
  setText("semantic-graph-edge-count", formatInteger(graph.edge_count || 0));

  const readinessState = readiness.ready ? "completed" : "failed";
  const warningCount = (readiness.warnings || []).length;
  const blockedCount = (readiness.blocked_reasons || []).length;
  const nextActions = readiness.next_actions || [];
  renderStackCards(summaryContainer, [
    `
      <article class="status-card">
        <header>
          <strong>Backfill readiness</strong>
          <span class="status-pill ${readinessState}">${readiness.ready ? "ready" : "blocked"}</span>
        </header>
        <div class="status-meta">
          <span>${status.semantics_enabled ? "semantic execution enabled" : "semantic execution disabled"}</span>
          <span>${formatInteger(missingPasses)} missing current passes</span>
          <span>${formatInteger(warningCount)} warnings</span>
          <span>${formatInteger(blockedCount)} blockers</span>
        </div>
        <p>${escapeHtml(compactList(nextActions, 3))}</p>
        ${renderCheckStrip([
          {
            label: "semantics enabled",
            state: status.semantics_enabled ? "passed" : "failed",
          },
          {
            label: "ontology concepts",
            state: registry.concept_count ? "passed" : "warning",
          },
          {
            label: "fact relation",
            state: (registry.relation_keys || []).includes("document_mentions_concept")
              ? "passed"
              : "warning",
          },
          {
            label: "active graph",
            state: graph.edge_count ? "passed" : "neutral",
          },
        ])}
      </article>
    `,
    `
      <article class="stack-card">
        <header>
          <strong>Active ontology</strong>
          <span class="meta-pill">${escapeHtml(registry.registry_version || "not initialized")}</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(registry.concept_count || 0)} concepts</span>
          <span>${formatInteger(registry.category_count || 0)} categories</span>
          <span>${formatInteger(registry.relation_count || 0)} relations</span>
        </div>
        <p>${escapeHtml(compactList(registry.relation_keys || [], 5))}</p>
      </article>
    `,
    `
      <article class="stack-card">
        <header>
          <strong>Semantic artifacts</strong>
          <span class="meta-pill">${formatInteger(status.fact_count || 0)} facts</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(status.assertion_count || 0)} assertions</span>
          <span>${formatInteger(status.evidence_count || 0)} evidence refs</span>
          <span>${formatInteger(status.entity_count || 0)} entities</span>
        </div>
        <p>${escapeHtml(formatJson(status.semantic_pass_counts || {}))}</p>
      </article>
    `,
    `
      <article class="stack-card">
        <header>
          <strong>Cross-document graph</strong>
          <span class="meta-pill">${escapeHtml(graph.graph_version || "not promoted")}</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(graph.node_count || 0)} nodes</span>
          <span>${formatInteger(graph.edge_count || 0)} edges</span>
          <span>${escapeHtml(graph.active_snapshot_id || "no active snapshot")}</span>
        </div>
        <p>${escapeHtml(graph.edge_count ? "Approved graph memory is available to generation." : "Graph memory is still awaiting build, evaluation, and promotion.")}</p>
      </article>
    `,
    ...(blockedCount + warningCount
      ? [
          `
            <article class="stack-card">
              <header>
                <strong>Backfill notes</strong>
                <span class="meta-pill">${formatInteger(blockedCount + warningCount)} items</span>
              </header>
              <p>${escapeHtml(compactList([...(readiness.blocked_reasons || []), ...(readiness.warnings || [])], 6))}</p>
            </article>
          `,
        ]
      : []),
  ]);

  const missingDocuments = status.sample_missing_documents || [];
  if (!missingDocuments.length) {
    renderEmpty(missingContainer, "No sampled active documents are missing the current semantic pass.");
    return;
  }
  renderStackCards(
    missingContainer,
    missingDocuments.map(
      (document) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(document.source_filename)}</strong>
            <span class="meta-pill">${escapeHtml(shortId(document.document_id))}</span>
          </header>
          <div class="status-meta">
            <span>${escapeHtml(document.latest_semantic_status || "no semantic pass")}</span>
            <span>${escapeHtml(document.latest_registry_version || "no registry")}</span>
            <span>${escapeHtml(shortId(document.active_run_id))}</span>
          </div>
        </article>
      `,
    ),
  );
}

function renderSemanticBackfillRunOutput(runState) {
  const container = byId("semantic-backfill-run-output");
  if (!container) {
    return;
  }
  if (runState.error) {
    renderEmpty(container, formatApiError(runState.error, "Semantic backfill failed."));
    return;
  }
  const payload = runState.data;
  if (!payload) {
    renderEmpty(container, "No semantic backfill slice has been run from this browser session.");
    return;
  }
  renderStackCards(container, [
    `
      <article class="status-card">
        <header>
          <strong>${payload.dry_run ? "Dry-run plan" : "Backfill execution"}</strong>
          <span class="meta-pill">${escapeHtml(formatDateTime(payload.completed_at))}</span>
        </header>
        <div class="status-meta">
          <span>${formatInteger(payload.processed_document_count || 0)} processed</span>
          <span>${formatInteger(payload.skipped_document_count || 0)} skipped</span>
          <span>${formatInteger(payload.failed_document_count || 0)} failed</span>
          <span>${formatInteger(payload.fact_graph_count || 0)} fact graphs</span>
        </div>
        <p>${formatInteger(payload.semantic_pass_count || 0)} semantic passes and ${formatInteger(payload.fact_count || 0)} facts in this slice.</p>
      </article>
    `,
    ...(payload.documents || []).slice(0, 8).map(
      (document) => `
        <article class="stack-card">
          <header>
            <strong>${escapeHtml(document.source_filename)}</strong>
            <span class="status-pill ${document.status === "failed" || document.status === "fact_graph_failed" ? "failed" : document.status === "planned" ? "queued" : "completed"}">${escapeHtml(formatStatusLabel(document.status))}</span>
          </header>
          <div class="status-meta">
            <span>${escapeHtml(document.action)}</span>
            <span>${formatInteger(document.assertion_count || 0)} assertions</span>
            <span>${formatInteger(document.fact_count || 0)} facts</span>
          </div>
          <p>${escapeHtml(document.error_message || `Semantic pass ${shortId(document.semantic_pass_id)}`)}</p>
        </article>
      `,
    ),
  ]);
}

async function refreshSemanticBackfillStatus() {
  const statusState = await fetchState("/semantics/backfill/status");
  renderSemanticBackfillStatus(statusState);
  return statusState;
}

async function loadSemanticsPage() {
  const statusState = await refreshSemanticBackfillStatus();
  if (statusState.error) {
    recordActivity(
      "Semantic status unavailable",
      formatApiError(statusState.error, "Unable to load semantic backfill status."),
      "error",
    );
  } else {
    recordActivity(
      "Semantic workspace ready",
      `${formatInteger(statusState.data?.active_current_pass_count || 0)} / ${formatInteger(statusState.data?.active_document_count || 0)} active documents have current semantic passes.`,
      "success",
    );
  }

  byId("semantic-backfill-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      limit: Number(byId("semantic-backfill-limit")?.value || 10),
      dry_run: byId("semantic-backfill-mode")?.value !== "execute",
      force: Boolean(byId("semantic-backfill-force")?.checked),
      build_fact_graphs: Boolean(byId("semantic-backfill-facts")?.checked),
    };
    setNote(
      "semantic-backfill-note",
      payload.dry_run ? "Planning a read-only backfill slice." : "Executing semantic backfill slice.",
    );
    const runState = await fetchState("/semantics/backfill", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderSemanticBackfillRunOutput(runState);
    if (runState.error) {
      setNote(
        "semantic-backfill-note",
        formatApiError(runState.error, "Semantic backfill failed."),
        true,
      );
      recordActivity(
        "Semantic backfill failed",
        formatApiError(runState.error, "Semantic backfill failed."),
        "error",
      );
      return;
    }
    setNote("semantic-backfill-note", "Semantic backfill slice completed.");
    recordActivity(
      payload.dry_run ? "Semantic backfill planned" : "Semantic backfill completed",
      `${formatInteger(runState.data?.processed_document_count || 0)} processed, ${formatInteger(runState.data?.failed_document_count || 0)} failed.`,
      runState.data?.failed_document_count ? "error" : "success",
    );
    if (runState.data?.status_after) {
      renderSemanticBackfillStatus({ data: runState.data.status_after });
    } else {
      await refreshSemanticBackfillStatus();
    }
  });
}

