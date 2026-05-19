const harnessCopy = {
  default_v1: {
    title: "default_v1",
    summary: "Production baseline tuned for stable mixed retrieval over active chunks and tables.",
    reason:
      "Use it when you want the safest default behavior and the reference point for all comparisons.",
  },
  wide_v2: {
    title: "wide_v2",
    summary: "Wider retrieval profile that increases candidate recall before reranking.",
    reason:
      "Agents compare against it when they suspect the default is missing evidence too early.",
  },
  prose_v3: {
    title: "prose_v3",
    summary: "Prose-oriented experiment that expands candidate generation for prose-heavy questions.",
    reason:
      "Agents use it when regressions look like context loss or cross-document prose ranking issues.",
  },
};

function makeHarnessDescription(row) {
  const builtIn = harnessCopy[row.harness_name];
  if (builtIn) {
    return builtIn;
  }
  const metadata = row.harness_config?.metadata || {};
  const base = row.harness_config?.base_harness_name || "custom base";
  if (metadata.override_type === "applied_harness_config_update") {
    return {
      title: row.harness_name,
      summary: `Applied review harness derived from ${base}.`,
      reason: "Published only after a verified draft and explicit approval.",
    };
  }
  return {
    title: row.harness_name,
    summary: "Additional registered retrieval harness.",
    reason: "Treat it as a reviewable configuration with explicit retrieval and reranking behavior.",
  };
}

function renderHarnessCards(container, harnesses, compact = false) {
  if (!container) {
    return;
  }
  if (!harnesses?.length) {
    renderEmpty(container, "Harnesses will appear here.");
    return;
  }
  container.className = compact ? "stack-list" : "feature-grid";
  container.innerHTML = harnesses
    .map((row) => {
      const copy = makeHarnessDescription(row);
      return `
        <article class="${compact ? "stack-card" : "feature-card"}">
          <header>
            <strong>${escapeHtml(copy.title)}</strong>
            <span class="meta-pill">${row.is_default ? "default" : escapeHtml(row.retrieval_profile_name)}</span>
          </header>
          <p>${escapeHtml(copy.summary)}</p>
          <p>${escapeHtml(copy.reason)}</p>
        </article>
      `;
    })
    .join("");
}

function buildSearchResultCard(result, { logged = false } = {}) {
  const label = result.result_type === "table" ? "Table evidence" : "Chunk evidence";
  const title =
    result.result_type === "table"
      ? result.table_title || result.table_heading || "Untitled table"
      : result.heading || "Prose chunk";
  const body = result.result_type === "table" ? result.table_preview || "" : result.chunk_text || "";
  const scoreItems = [
    `overall ${formatDecimal(result.score, 3)}`,
    result.scores?.hybrid_score != null ? `hybrid ${formatDecimal(result.scores.hybrid_score, 3)}` : "",
    result.scores?.keyword_score != null ? `keyword ${formatDecimal(result.scores.keyword_score, 3)}` : "",
    result.scores?.semantic_score != null ? `semantic ${formatDecimal(result.scores.semantic_score, 3)}` : "",
  ].filter(Boolean);
  const rankMeta = logged && result.rank ? `<span>rank ${formatInteger(result.rank)}</span>` : "";
  const docLink = internalLink(
    `/ui/documents.html?document_id=${encodeURIComponent(result.document_id)}`,
    "Open document",
  );
  const shapeMeta =
    result.result_type === "table" && result.row_count != null && result.col_count != null
      ? `<span>${formatInteger(result.row_count)} rows x ${formatInteger(result.col_count)} cols</span>`
      : `<span>${escapeHtml(result.result_type === "table" ? "structured evidence" : "prose evidence")}</span>`;

  return `
    <article class="result-card">
      <header>
        <strong>${escapeHtml(title)}</strong>
        <span class="meta-pill">${escapeHtml(label)}</span>
      </header>
      <div class="result-meta">
        <span>${escapeHtml(result.source_filename)}</span>
        <span>${escapeHtml(formatPageRange(result.page_from, result.page_to))}</span>
        ${rankMeta}
        ${shapeMeta}
      </div>
      <div class="score-strip">
        ${scoreItems.map((item) => `<span class="score-chip">${escapeHtml(item)}</span>`).join("")}
      </div>
      <div class="result-snippet ${result.result_type === "table" ? "is-tabular" : ""}">
        ${escapeHtml(body || "No evidence text recorded for this result.")}
      </div>
      <div class="artifact-actions">
        ${docLink}
      </div>
    </article>
  `;
}
