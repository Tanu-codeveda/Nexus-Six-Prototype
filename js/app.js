/**
 * App controller: fetches complaints from the Core API, applies the
 * filter panel, and keeps the map / queue table / detail panel /
 * analytics in sync.
 */
(function () {
  const cfg = window.CivicPulseConfig;
  const api = window.CivicPulseAPI;

  let allComplaints = [];
  let selectedId = null;
  let filters = { category: new Set(), severity: new Set(), status: new Set(), dept: "", search: "" };
  let firstLoad = true;
  let previousIds = new Set();

  function haversineKm(a, b) {
    const R = 6371;
    const dLat = (b.latitude - a.latitude) * Math.PI / 180;
    const dLon = (b.longitude - a.longitude) * Math.PI / 180;
    const x = Math.sin(dLat/2)**2 + Math.cos(a.latitude*Math.PI/180) * Math.cos(b.latitude*Math.PI/180) * Math.sin(dLon/2)**2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  function showAdminToast(message) {
    const el = document.getElementById("adminToast");
    if (!el) return;
    el.textContent = message;
    el.classList.add("is-visible");
    clearTimeout(window.__cpToastTimer);
    window.__cpToastTimer = setTimeout(() => el.classList.remove("is-visible"), 4500);
  }

  function priorityScore(c) {
    const base = { Critical: 100, High: 80, Medium: 55, Low: 30 }[c.ai_severity] || 30;
    const nearby = allComplaints.filter(x => x.id !== c.id && typeof x.latitude === "number" && typeof x.longitude === "number" && typeof c.latitude === "number" && typeof c.longitude === "number" && haversineKm(c, x) <= 0.65).length;
    return Math.min(100, base + Math.min(20, nearby * 5));
  }

  function findDuplicates(c) {
    if (typeof c.latitude !== "number" || typeof c.longitude !== "number") return [];
    const words = new Set((c.description || "").toLowerCase().split(/\W+/).filter((w) => w.length >= 4));
    return allComplaints
      .filter((x) => {
        if (x.id === c.id || typeof x.latitude !== "number" || typeof x.longitude !== "number") return false;
        const distance = haversineKm(c, x);
        if (distance > 0.35) return false;
        if (c.ai_category && x.ai_category && c.ai_category !== x.ai_category) return false;
        const other = new Set((x.description || "").toLowerCase().split(/\W+/).filter((w) => w.length >= 4));
        const shared = [...words].filter((w) => other.has(w)).length;
        const union = new Set([...words, ...other]).size || 1;
        const similarity = shared / union;
        const recent = c.created_at && x.created_at
          ? Math.abs(new Date(c.created_at).getTime() - new Date(x.created_at).getTime()) <= 24 * 60 * 60 * 1000
          : false;
        return similarity >= 0.25 || (recent && shared >= 1);
      })
      .sort((a, b) => haversineKm(c, a) - haversineKm(c, b))
      .slice(0, 5);
  }

  // ---------- boot ----------
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
    document.getElementById("refreshBtn").addEventListener("click", loadComplaints);
    document.getElementById("exportBtn")?.addEventListener("click", exportCsv);
    document.getElementById("clearFilters").addEventListener("click", clearFilters);

    document.getElementById("filterSearch").addEventListener("input", (e) => {
      filters.search = e.target.value.trim().toLowerCase();
      applyFiltersAndRender();
    });
    document.getElementById("filterDept").addEventListener("change", (e) => {
      filters.dept = e.target.value;
      applyFiltersAndRender();
    });

    document.getElementById("detailSave").addEventListener("click", saveDetail);
  }

  // ---------- filter panel ----------
  function buildFilterChips() {
    renderChipGroup("filterCategory", cfg.CATEGORIES, filters.category);
    renderChipGroup("filterSeverity", cfg.SEVERITIES, filters.severity);
    renderChipGroup("filterStatus", cfg.STATUSES, filters.status);
  }

  function renderChipGroup(containerId, values, targetSet) {
    const container = document.getElementById(containerId);
    container.innerHTML = values
      .map((v) => `<button class="chip" type="button" aria-pressed="false" data-value="${v}">${v}</button>`)
      .join("");
    container.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const v = chip.dataset.value;
        const pressed = chip.getAttribute("aria-pressed") === "true";
        chip.setAttribute("aria-pressed", String(!pressed));
        if (pressed) targetSet.delete(v);
        else targetSet.add(v);
        applyFiltersAndRender();
      });
    });
  }

  function buildSelectOptions() {
    const deptFilter = document.getElementById("filterDept");
    cfg.DEPARTMENTS.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      deptFilter.appendChild(opt);
    });

    const deptDetail = document.getElementById("detailDeptSelect");
    cfg.DEPARTMENTS.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      deptDetail.appendChild(opt);
    });
  }

  function clearFilters() {
    filters = { category: new Set(), severity: new Set(), status: new Set(), dept: "", search: "" };
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
    document.getElementById("filterDept").value = "";
    document.getElementById("filterSearch").value = "";
    applyFiltersAndRender();
  }

  function getFiltered() {
    return allComplaints.filter((c) => {
      if (filters.category.size && !filters.category.has(c.ai_category)) return false;
      if (filters.severity.size && !filters.severity.has(c.ai_severity)) return false;
      if (filters.status.size && !filters.status.has(c.status)) return false;
      if (filters.dept && c.assigned_department !== filters.dept) return false;
      if (filters.search) {
        const hay = `${c.description || ""} ${c.latitude || ""} ${c.longitude || ""}`.toLowerCase();
        if (!hay.includes(filters.search)) return false;
      }
      return true;
    });
  }

  // ---------- data load ----------
  async function loadComplaints() {
    try {
      const freshComplaints = await api.getComplaints();
      const freshIds = new Set(freshComplaints.map(c => c.id));
      if (!firstLoad) {
        const added = freshComplaints.filter(c => !previousIds.has(c.id));
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
      document.getElementById("tickerTime").textContent = "connection error";
    }
  }

  function updateTicker() {
    const pending = allComplaints.filter((c) => c.status === "Pending").length;
    const critical = allComplaints.filter((c) => c.ai_severity === "Critical").length;
    document.getElementById("tickerPending").textContent = pending;
    document.getElementById("tickerCritical").textContent = critical;
    document.getElementById("tickerTime").textContent = new Date().toLocaleTimeString();
  }

  function applyFiltersAndRender() {
    const filtered = getFiltered();

    const activeCount = filters.category.size + filters.severity.size + filters.status.size + (filters.dept ? 1 : 0) + (filters.search ? 1 : 0);
    document.getElementById("filterSummary").textContent = activeCount
      ? `${filtered.length} of ${allComplaints.length} reports match`
      : "Showing all reports";

    CivicPulseMap.render(filtered);
    CivicPulseTable.render(filtered, selectedId, selectComplaint);
    CivicPulseAnalytics.renderAll(filtered);
    updateOperationalMetrics(filtered);
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
    const ackTimes = items.map(c => minutesBetween(c.created_at, c.acknowledged_at)).filter(v => v !== null);
    const resTimes = items.map(c => minutesBetween(c.created_at, c.resolved_at)).filter(v => v !== null);
    const avg = values => values.length ? values.reduce((a,b) => a+b, 0) / values.length : null;
    const resolved = items.filter(c => c.status === "Resolved").length;
    const highRisk = items.filter(c => c.ai_severity === "High" || c.ai_severity === "Critical").length;
    const ack = document.getElementById("metricAck");
    const resolution = document.getElementById("metricResolution");
    const resolvedRate = document.getElementById("metricResolvedRate");
    const highRiskEl = document.getElementById("metricHighRisk");
    if (ack) ack.textContent = formatDuration(avg(ackTimes));
    if (resolution) resolution.textContent = formatDuration(avg(resTimes));
    if (resolvedRate) resolvedRate.textContent = items.length ? `${Math.round(resolved / items.length * 100)}%` : "—";
    if (highRiskEl) highRiskEl.textContent = items.length ? `${highRisk} / ${items.length}` : "—";
  }

  function csvEscape(value) {
    const text = value == null ? "" : String(value);
    return `"${text.replace(/"/g, '""')}"`;
  }

  function exportCsv() {
    const rows = getFiltered();
    if (!rows.length) { showAdminToast("No visible reports to export"); return; }
    const headers = ["id","latitude","longitude","description","ai_category","ai_severity","status","assigned_department","created_at","acknowledged_at","in_progress_at","resolved_at","updated_at","verification_count","last_verified_at","estimated_resolution_hours","probable_root_cause"];
    const csv = [headers.join(","), ...rows.map(r => headers.map(h => csvEscape(r[h])).join(","))].join("\r\n");
    const blob = new Blob([csv], {type:"text/csv;charset=utf-8;"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `civicpulse-reports-${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showAdminToast(`Exported ${rows.length} report${rows.length === 1 ? "" : "s"}`);
  }

  function formatDateTime(value) {
    if (!value) return "—";
    const d = new Date(value);
    if (!Number.isFinite(d.getTime())) return "—";
    return d.toLocaleString(undefined, {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit"
    });
  }

  // ---------- detail panel ----------
  function selectComplaint(id) {
    selectedId = id;
    const c = allComplaints.find((x) => x.id === id);
    if (!c) return;

    document.getElementById("detailEmpty").hidden = true;
    const content = document.getElementById("detailContent");
    content.hidden = false;

    document.getElementById("detailId").textContent = c.id;
    document.getElementById("detailCategory").textContent = c.ai_category || "General Maintenance";
    document.getElementById("detailDescription").textContent = c.description || "No description provided.";
    document.getElementById("detailLocation").textContent =
      typeof c.latitude === "number" ? `${c.latitude.toFixed(5)}, ${c.longitude.toFixed(5)}` : "Not tagged";
    document.getElementById("detailCreated").textContent = formatDateTime(c.created_at);
    document.getElementById("detailAcknowledged").textContent = formatDateTime(c.acknowledged_at);
    document.getElementById("detailInProgress").textContent = formatDateTime(c.in_progress_at);
    document.getElementById("detailResolved").textContent = formatDateTime(c.resolved_at);
    const updatedEl = document.getElementById("detailUpdated");
    if (updatedEl) updatedEl.textContent = formatDateTime(c.updated_at || c.created_at);
    document.getElementById("detailSeverity").textContent = c.ai_severity || "Low";
    const verifyEl = document.getElementById("detailVerification");
    if (verifyEl) verifyEl.textContent = `${c.verification_count || 0} confirmations`;
    const rootEl = document.getElementById("detailRootCause");
    if (rootEl) rootEl.textContent = c.probable_root_cause || "Not available";
    const estimateEl = document.getElementById("detailEstimate");
    if (estimateEl) estimateEl.textContent = c.estimated_resolution_hours ? `${c.estimated_resolution_hours} h` : "—";

    const priorityEl = document.getElementById("detailPriority");
    if (priorityEl) {
      priorityEl.hidden = false;
      priorityEl.innerHTML = `<strong>Operational priority: ${priorityScore(c)}/100</strong><br>Severity + nearby report density`;
    }
    const duplicateEl = document.getElementById("detailDuplicates");
    const duplicates = findDuplicates(c);
    if (duplicateEl) {
      duplicateEl.hidden = duplicates.length === 0;
      duplicateEl.innerHTML = duplicates.length ? `<strong>Potential duplicate reports (${duplicates.length})</strong>${duplicates.map(x => `<div><a href="#" data-dup-id="${x.id}">#${x.id.slice(0,8).toUpperCase()}</a> · ${x.ai_category || "Unclassified"}</div>`).join("")}` : "";
      duplicateEl.querySelectorAll('[data-dup-id]').forEach(a => a.addEventListener('click', (e) => { e.preventDefault(); selectComplaint(a.dataset.dupId); }));
    }

    const media = document.getElementById("detailMedia");
    if (c.media_url) {
      media.src = c.media_url;
      media.hidden = false;
    } else {
      media.hidden = true;
    }

    document.getElementById("detailStatusSelect").value = c.status || "Pending";
    document.getElementById("detailDeptSelect").value = c.assigned_department || "Unassigned";
    document.getElementById("detailSaveMsg").textContent = "";

    applyFiltersAndRender();
    CivicPulseMap.highlight(id, allComplaints);
  }

  async function saveDetail() {
    if (!selectedId) return;
    const status = document.getElementById("detailStatusSelect").value;
    const assigned_department = document.getElementById("detailDeptSelect").value;
    const msg = document.getElementById("detailSaveMsg");
    msg.textContent = "Saving…";

    try {
      const updated = await api.updateComplaint(selectedId, { status, assigned_department });
      const idx = allComplaints.findIndex((c) => c.id === selectedId);
      if (idx !== -1) allComplaints[idx] = updated;
      msg.textContent = "Saved.";
      updateTicker();
      selectComplaint(selectedId);
    } catch (err) {
      msg.textContent = `Could not save: ${err.message}`;
      console.error("Could not save complaint:", err);
    }
  }
})();
