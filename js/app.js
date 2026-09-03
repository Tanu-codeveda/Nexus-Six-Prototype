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

  // ---------- boot ----------
  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("apiBaseInput").value = cfg.apiBase;
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
    document.getElementById("clearFilters").addEventListener("click", clearFilters);

    document.getElementById("settingsBtn").addEventListener("click", () => {
      document.getElementById("settingsDrawer").hidden = false;
    });
    document.getElementById("settingsCancel").addEventListener("click", () => {
      document.getElementById("settingsDrawer").hidden = true;
    });
    document.getElementById("settingsSave").addEventListener("click", () => {
      const val = document.getElementById("apiBaseInput").value.trim();
      if (val) cfg.apiBase = val;
      document.getElementById("settingsDrawer").hidden = true;
      loadComplaints();
    });

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
      allComplaints = await api.getComplaints();
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
    document.getElementById("detailCreated").textContent = c.created_at ? new Date(c.created_at).toLocaleString() : "—";
    document.getElementById("detailSeverity").textContent = c.ai_severity || "Low";

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
      applyFiltersAndRender();
    } catch (err) {
      msg.textContent = `Could not save: ${err.message}`;
    }
  }
})();
