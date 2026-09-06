/**
 * CivicPulse Ops controller. The API now returns operational intelligence so
 * the dashboard can explain priority, duplicates, predictive service time,
 * root-cause signals and citizen-facing progress updates.
 */
(function () {
  const cfg = window.CivicPulseConfig;
  const api = window.CivicPulseAPI;

  let allComplaints = [];
  let selectedId = null;
  let filters = { category: new Set(), severity: new Set(), status: new Set(), dept: "", search: "" };
  let firstLoad = true;
  let previousIds = new Set();
  let pendingResolutionEvidence;

  function showAdminToast(message) {
    const el = document.getElementById("adminToast");
    if (!el) return;
    el.textContent = message;
    el.classList.add("is-visible");
    clearTimeout(window.__cpToastTimer);
    window.__cpToastTimer = setTimeout(() => el.classList.remove("is-visible"), 4500);
  }

  document.addEventListener("DOMContentLoaded", () => {
    buildFilterChips();
    buildSelectOptions();
    CivicPulseMap.init(selectComplaint);
    CivicPulseTable.bindHeaders(applyFiltersAndRender);
    bindGlobalControls();
    loadComplaints();
    setInterval(loadComplaints, cfg.REFRESH_INTERVAL_MS);
  });

  function bindGlobalControls() {
    document.getElementById("refreshBtn")?.addEventListener("click", loadComplaints);
    document.getElementById("exportBtn")?.addEventListener("click", exportCsv);
    document.getElementById("clearFilters")?.addEventListener("click", clearFilters);
    document.getElementById("filterSearch")?.addEventListener("input", (e) => {
      filters.search = e.target.value.trim().toLowerCase();
      applyFiltersAndRender();
    });
    document.getElementById("filterDept")?.addEventListener("change", (e) => {
      filters.dept = e.target.value;
      applyFiltersAndRender();
    });
    document.getElementById("detailSave")?.addEventListener("click", saveDetail);
    document.getElementById("detailResolutionEvidence")?.addEventListener("change", handleResolutionEvidence);
    document.getElementById("detailStatusSelect")?.addEventListener("change", updateResolutionEvidenceState);
  }

  function buildFilterChips() {
    renderChipGroup("filterCategory", cfg.CATEGORIES, filters.category);
    renderChipGroup("filterSeverity", cfg.SEVERITIES, filters.severity);
    renderChipGroup("filterStatus", cfg.STATUSES, filters.status);
  }

  function renderChipGroup(containerId, values, targetSet) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = values.map((value) => `<button class="chip" type="button" aria-pressed="false" data-value="${value}">${value}</button>`).join("");
    container.querySelectorAll(".chip").forEach((chip) => chip.addEventListener("click", () => {
      const value = chip.dataset.value;
      const pressed = chip.getAttribute("aria-pressed") === "true";
      chip.setAttribute("aria-pressed", String(!pressed));
      if (pressed) targetSet.delete(value); else targetSet.add(value);
      applyFiltersAndRender();
    }));
  }

  function buildSelectOptions() {
    const deptFilter = document.getElementById("filterDept");
    const deptDetail = document.getElementById("detailDeptSelect");
    cfg.DEPARTMENTS.forEach((dept) => {
      const option1 = document.createElement("option"); option1.value = dept; option1.textContent = dept; deptFilter?.appendChild(option1);
      const option2 = document.createElement("option"); option2.value = dept; option2.textContent = dept; deptDetail?.appendChild(option2);
    });
  }

  function clearFilters() {
    filters = { category: new Set(), severity: new Set(), status: new Set(), dept: "", search: "" };
    document.querySelectorAll(".chip").forEach((chip) => chip.setAttribute("aria-pressed", "false"));
    const dept = document.getElementById("filterDept"); if (dept) dept.value = "";
    const search = document.getElementById("filterSearch"); if (search) search.value = "";
    applyFiltersAndRender();
  }

  function getFiltered() {
    return allComplaints.filter((c) => {
      if (filters.category.size && !filters.category.has(c.ai_category)) return false;
      if (filters.severity.size && !filters.severity.has(c.ai_severity)) return false;
      if (filters.status.size && !filters.status.has(c.status)) return false;
      if (filters.dept && c.assigned_department !== filters.dept) return false;
      if (filters.search) {
        const hay = [
          c.description, c.voice_transcript, c.ai_category, c.assigned_department,
          c.probable_root_cause, c.recommended_action, c.priority_reason,
          c.latitude, c.longitude,
        ].filter(Boolean).join(" ").toLowerCase();
        if (!hay.includes(filters.search)) return false;
      }
      return true;
    });
  }

  async function loadComplaints() {
    try {
      const freshComplaints = await api.getComplaints();
      const freshIds = new Set(freshComplaints.map((c) => c.id));
      if (!firstLoad) {
        const added = freshComplaints.filter((c) => !previousIds.has(c.id));
        if (added.length) {
          const first = added[0];
          showAdminToast(`${added.length} new complaint${added.length > 1 ? "s" : ""} received${first?.ai_category ? ` · ${first.ai_category}` : ""}`);
        }
      }
      allComplaints = freshComplaints;
      previousIds = freshIds;
      firstLoad = false;
      updateTicker();
      applyFiltersAndRender();
    } catch (err) {
      console.error("Failed to load complaints:", err);
      const ticker = document.getElementById("tickerTime"); if (ticker) ticker.textContent = "connection error";
    }
  }

  function updateTicker() {
    const pending = allComplaints.filter((c) => c.status === "Pending").length;
    const critical = allComplaints.filter((c) => c.ai_severity === "Critical").length;
    const hotspots = allComplaints.filter((c) => Number(c.nearby_report_count || 0) >= 3 && c.status !== "Resolved").length;
    const delayed = allComplaints.filter((c) => (c.is_overdue || c.delay_reason || c.is_escalated) && c.status !== "Resolved").length;
    document.getElementById("tickerPending").textContent = pending;
    document.getElementById("tickerCritical").textContent = critical;
    document.getElementById("tickerHotspots").textContent = hotspots;
    const delayedEl = document.getElementById("tickerDelayed"); if (delayedEl) delayedEl.textContent = delayed;
    document.getElementById("tickerTime").textContent = new Date().toLocaleTimeString();
  }

  function applyFiltersAndRender() {
    const filtered = getFiltered();
    const activeCount = filters.category.size + filters.severity.size + filters.status.size + (filters.dept ? 1 : 0) + (filters.search ? 1 : 0);
    const summary = document.getElementById("filterSummary");
    if (summary) summary.textContent = activeCount ? `${filtered.length} of ${allComplaints.length} reports match` : "Showing all reports";
    CivicPulseMap.render(filtered);
    CivicPulseTable.render(filtered, selectedId, selectComplaint);
    CivicPulseAnalytics.renderAll(filtered);
    updateOperationalMetrics(filtered);
    renderIntelligenceSummary(filtered);
  }

  function minutesBetween(start, end) {
    if (!start || !end) return null;
    const a = new Date(start).getTime();
    const b = new Date(end).getTime();
    if (!Number.isFinite(a) || !Number.isFinite(b) || b < a) return null;
    return (b - a) / 60000;
  }

  function formatDuration(minutes) {
    if (minutes === null || !Number.isFinite(minutes)) return "—";
    if (minutes < 1) return "<1 min";
    if (minutes < 60) return `${Math.round(minutes)} min`;
    const hours = minutes / 60;
    if (hours < 24) return `${hours.toFixed(1)} h`;
    return `${(hours / 24).toFixed(1)} d`;
  }

  function updateOperationalMetrics(items) {
    const ackTimes = items.map((c) => minutesBetween(c.created_at, c.acknowledged_at)).filter((v) => v !== null);
    const resTimes = items.map((c) => minutesBetween(c.created_at, c.resolved_at)).filter((v) => v !== null);
    const avg = (values) => values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
    const resolved = items.filter((c) => c.status === "Resolved").length;
    const highRisk = items.filter((c) => c.ai_severity === "High" || c.ai_severity === "Critical").length;
    const hotspotReports = items.filter((c) => Number(c.nearby_report_count || 0) >= 3 && c.status !== "Resolved").length;
    const avgPrediction = items.map((c) => Number(c.estimated_resolution_hours)).filter(Number.isFinite);

    const set = (id, value) => { const element = document.getElementById(id); if (element) element.textContent = value; };
    set("metricAck", formatDuration(avg(ackTimes)));
    set("metricResolution", formatDuration(avg(resTimes)));
    set("metricResolvedRate", items.length ? `${Math.round(resolved / items.length * 100)}%` : "—");
    set("metricHighRisk", items.length ? `${highRisk} / ${items.length}` : "—");
    set("metricHotspots", hotspotReports ? String(hotspotReports) : "0");
    set("metricPrediction", avgPrediction.length ? formatDuration(avg(avgPrediction) * 60) : "—");
  }

  function renderIntelligenceSummary(items) {
    const box = document.getElementById("intelligenceSummary");
    if (!box) return;
    const open = items.filter((c) => c.status !== "Resolved");
    const top = [...open].sort((a, b) => Number(b.priority_score || 0) - Number(a.priority_score || 0))[0];
    const cluster = [...open].sort((a, b) => Number(b.nearby_report_count || 0) - Number(a.nearby_report_count || 0))[0];
    if (!top) {
      box.innerHTML = "<strong>No active priority signals.</strong><span>New reports will be analysed automatically.</span>";
      return;
    }
    box.innerHTML = `
      <strong>Highest current priority: ${Number(top.priority_score || 0)}/100</strong>
      <span>#${String(top.id).slice(0, 8).toUpperCase()} · ${escapeHtml(top.ai_category || "General Maintenance")}</span>
      <small>${escapeHtml(top.priority_reason || "Severity and local report context")}</small>
      ${cluster && Number(cluster.nearby_report_count || 0) >= 3 ? `<small>Hotspot signal: ${Number(cluster.nearby_report_count)} nearby active reports around #${String(cluster.id).slice(0, 8).toUpperCase()}.</small>` : ""}`;
  }

  function escapeHtml(value) { return String(value ?? "").replace(/[&<>\"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[char])); }

  function csvEscape(value) { const text = value == null ? "" : String(value); return `"${text.replace(/"/g, '""')}"`; }
  function exportCsv() {
    const rows = getFiltered();
    if (!rows.length) { showAdminToast("No visible reports to export"); return; }
    const headers = ["id", "latitude", "longitude", "description", "voice_transcript", "ai_category", "ai_severity", "ai_confidence_score", "status", "assigned_department", "priority_score", "priority_reason", "nearby_report_count", "duplicate_count", "verification_count", "created_at", "acknowledged_at", "in_progress_at", "resolved_at", "updated_at", "estimated_resolution_hours", "prediction_basis", "probable_root_cause", "root_cause_factors", "recommended_action"];
    const csv = [headers.join(","), ...rows.map((row) => headers.map((key) => csvEscape(Array.isArray(row[key]) ? row[key].join(" | ") : row[key])).join(","))].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `civicpulse-reports-${new Date().toISOString().slice(0, 10)}.csv`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    showAdminToast(`Exported ${rows.length} report${rows.length === 1 ? "" : "s"}`);
  }

  function formatDateTime(value) {
    if (!value) return "—";
    const d = new Date(value);
    return Number.isFinite(d.getTime()) ? d.toLocaleString(undefined, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—";
  }

  function selectComplaint(id) {
    selectedId = id;
    const c = allComplaints.find((item) => item.id === id);
    if (!c) return;

    document.getElementById("detailEmpty").hidden = true;
    document.getElementById("detailContent").hidden = false;
    document.getElementById("detailId").textContent = c.id;
    document.getElementById("detailCategory").textContent = c.ai_category || "General Maintenance";
    document.getElementById("detailDescription").textContent = c.description || "No description provided.";
    document.getElementById("detailLocation").textContent = typeof c.latitude === "number" ? `${c.latitude.toFixed(5)}, ${c.longitude.toFixed(5)}` : "Not tagged";
    document.getElementById("detailCreated").textContent = formatDateTime(c.created_at);
    document.getElementById("detailAcknowledged").textContent = formatDateTime(c.acknowledged_at);
    document.getElementById("detailInProgress").textContent = formatDateTime(c.in_progress_at);
    document.getElementById("detailResolved").textContent = formatDateTime(c.resolved_at);
    const updatedEl = document.getElementById("detailUpdated"); if (updatedEl) updatedEl.textContent = formatDateTime(c.updated_at || c.created_at);
    document.getElementById("detailSeverity").textContent = c.ai_severity || "Low";

    const confidenceEl = document.getElementById("detailConfidence"); if (confidenceEl) confidenceEl.textContent = c.ai_confidence_score == null ? "—" : `${Math.round(Number(c.ai_confidence_score) * 100)}%`;
    const verifyEl = document.getElementById("detailVerification"); if (verifyEl) verifyEl.textContent = `${Number(c.verification_count || 0)} confirmation${Number(c.verification_count || 0) === 1 ? "" : "s"}`;
    const estimateEl = document.getElementById("detailEstimate"); if (estimateEl) estimateEl.textContent = c.estimated_resolution_hours ? `${c.estimated_resolution_hours} h` : "—";
    const basisEl = document.getElementById("detailPredictionBasis"); if (basisEl) basisEl.textContent = c.prediction_basis || "Prototype baseline";
    const rootEl = document.getElementById("detailRootCause"); if (rootEl) rootEl.textContent = c.probable_root_cause || "Not available";
    const factorsEl = document.getElementById("detailRootFactors"); if (factorsEl) factorsEl.textContent = (c.root_cause_factors || []).join(" · ") || "Not available";
    const actionEl = document.getElementById("detailRecommendedAction"); if (actionEl) actionEl.textContent = c.recommended_action || "Inspect the reported location.";

    const delayEl = document.getElementById("detailDelay");
    if (delayEl) {
      const delayed = Boolean(c.is_overdue) && c.status !== "Resolved";
      delayEl.hidden = !(delayed || c.is_escalated || c.delay_reason);
      if (delayed || c.is_escalated || c.delay_reason) {
        const labels = [];
        if (delayed) labels.push("SLA overdue");
        if (c.is_escalated) labels.push("Escalated");
        delayEl.innerHTML = `<strong>${labels.join(" · ")}</strong><span>${escapeHtml(c.delay_reason || "Projected service window has been exceeded.")}</span>`;
      }
    }

    const priorityEl = document.getElementById("detailPriority");
    if (priorityEl) {
      priorityEl.hidden = false;
      const score = Number(c.priority_score || 0);
      priorityEl.innerHTML = `<strong>Operational priority: ${score}/100</strong><span>${escapeHtml(c.priority_reason || "Severity + local context")}</span>`;
      priorityEl.classList.toggle("is-critical", score >= 85);
    }

    const duplicateEl = document.getElementById("detailDuplicates");
    const duplicateIds = Array.isArray(c.possible_duplicate_ids) ? c.possible_duplicate_ids : [];
    if (duplicateEl) {
      duplicateEl.hidden = duplicateIds.length === 0;
      duplicateEl.innerHTML = duplicateIds.length
        ? `<strong>Potential duplicate reports (${duplicateIds.length})</strong>${duplicateIds.map((dupId) => `<div><a href="#" data-dup-id="${escapeHtml(dupId)}">#${String(dupId).slice(0, 8).toUpperCase()}</a></div>`).join("")}`
        : `<strong>No likely duplicates detected</strong>`;
      duplicateEl.querySelectorAll("[data-dup-id]").forEach((anchor) => anchor.addEventListener("click", (event) => { event.preventDefault(); selectComplaint(anchor.dataset.dupId); }));
    }

    renderProgressTimeline(c.progress_updates || []);
    const media = document.getElementById("detailMedia");
    if (c.media_url) { media.src = c.media_url; media.hidden = false; } else { media.hidden = true; }
    pendingResolutionEvidence = undefined;
    const evidenceInput = document.getElementById("detailResolutionEvidence");
    const evidencePreview = document.getElementById("detailResolutionEvidencePreview");
    if (evidenceInput) evidenceInput.value = "";
    if (evidencePreview) { if (c.resolution_media_url) { evidencePreview.src = c.resolution_media_url; evidencePreview.hidden = false; } else { evidencePreview.hidden = true; evidencePreview.removeAttribute("src"); } }
    document.getElementById("detailStatusSelect").value = c.status || "Pending";
    updateResolutionEvidenceState();
    document.getElementById("detailDeptSelect").value = c.assigned_department || "Unassigned";
    const progressInput = document.getElementById("detailProgressMessage"); if (progressInput) progressInput.value = "";
    document.getElementById("detailSaveMsg").textContent = "";
    applyFiltersAndRender();
    CivicPulseMap.highlight(id, allComplaints);
  }

  function renderProgressTimeline(updates) {
    const container = document.getElementById("detailProgressTimeline");
    if (!container) return;
    if (!updates.length) { container.innerHTML = '<p class="muted">No progress updates yet.</p>'; return; }
    container.innerHTML = updates.slice().reverse().map((item) => `<div class="progress-event"><span>${formatDateTime(item.timestamp)}</span><strong>${escapeHtml(item.message)}</strong><em>${escapeHtml(item.kind || "system")}</em></div>`).join("");
  }

  function updateResolutionEvidenceState() {
    const status = document.getElementById("detailStatusSelect")?.value;
    const input = document.getElementById("detailResolutionEvidence");
    const label = document.querySelector(".resolution-evidence-field label");
    if (input) input.disabled = status !== "Resolved";
    if (label) label.classList.toggle("is-disabled", status !== "Resolved");
  }

  function handleResolutionEvidence(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) { showAdminToast("Please choose an image file."); event.target.value = ""; return; }
    if (file.size > 5 * 1024 * 1024) { showAdminToast("Completion evidence must be 5 MB or smaller."); event.target.value = ""; return; }
    const reader = new FileReader();
    reader.onload = () => {
      pendingResolutionEvidence = String(reader.result || "");
      const preview = document.getElementById("detailResolutionEvidencePreview");
      if (preview) { preview.src = pendingResolutionEvidence; preview.hidden = false; }
    };
    reader.onerror = () => showAdminToast("Could not read the completion evidence photo.");
    reader.readAsDataURL(file);
  }

  async function saveDetail() {
    if (!selectedId) return;
    const status = document.getElementById("detailStatusSelect").value;
    const assigned_department = document.getElementById("detailDeptSelect").value;
    const progress_message = document.getElementById("detailProgressMessage")?.value.trim() || null;
    const msg = document.getElementById("detailSaveMsg");
    msg.textContent = "Saving…";
    try {
      const patch = { status, assigned_department, progress_message };
      if (pendingResolutionEvidence !== undefined && status === "Resolved") patch.resolution_media_url = pendingResolutionEvidence;
      const updated = await api.updateComplaint(selectedId, patch);
      const idx = allComplaints.findIndex((c) => c.id === selectedId);
      if (idx !== -1) allComplaints[idx] = updated;
      msg.textContent = "Saved and published to citizen tracking.";
      updateTicker();
      selectComplaint(selectedId);
    } catch (err) {
      msg.textContent = `Could not save: ${err.message}`;
      console.error("Could not save complaint:", err);
    }
  }
})();
