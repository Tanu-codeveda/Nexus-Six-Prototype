window.CivicPulseTable = (function () {
  let sortKey = "created_at";
  let sortDir = "desc";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[char]));
  function severityBadge(severity) { const cls = (severity || "Low").toLowerCase(); return `<span class="badge badge--${cls}">${escapeHtml(severity || "Low")}</span>`; }
  function statusBadge(status) { return `<span class="badge badge--status">${escapeHtml(status || "Pending")}</span>`; }
  function formatTime(value) { if (!value) return "—"; const date = new Date(value); if (!Number.isFinite(date.getTime())) return "—"; return date.toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
  function formatLocation(c) { if (typeof c.latitude !== "number" || typeof c.longitude !== "number") return "—"; return `${c.latitude.toFixed(4)}, ${c.longitude.toFixed(4)}`; }
  function sort(items) { return [...items].sort((a, b) => { let av = a[sortKey] ?? ""; let bv = b[sortKey] ?? ""; if (["created_at","updated_at"].includes(sortKey)) { av = new Date(av).getTime() || 0; bv = new Date(bv).getTime() || 0; } else { av = String(av).toLowerCase(); bv = String(bv).toLowerCase(); } if (av < bv) return sortDir === "asc" ? -1 : 1; if (av > bv) return sortDir === "asc" ? 1 : -1; return 0; }); }
  function setSort(key) { if (sortKey === key) sortDir = sortDir === "asc" ? "desc" : "asc"; else { sortKey = key; sortDir = "asc"; } }
  function render(complaints, selectedId, onRowClick) {
    const body = document.getElementById("queueBody"); const emptyMsg = document.getElementById("queueEmptyMsg"); const countEl = document.getElementById("queueCount"); const sorted = sort(complaints);
    countEl.textContent = `${complaints.length} report${complaints.length === 1 ? "" : "s"}`;
    if (!sorted.length) { body.innerHTML = ""; emptyMsg.hidden = false; return; }
    emptyMsg.hidden = true;
    body.innerHTML = sorted.map((c) => `<tr data-id="${escapeHtml(c.id)}" class="${c.id === selectedId ? "is-selected" : ""}"><td class="mono">${escapeHtml(c.id.slice(0,8))}</td><td>${escapeHtml(c.ai_category || "General Maintenance")}</td><td>${severityBadge(c.ai_severity)}</td><td>${statusBadge(c.status)}</td><td>${escapeHtml(c.assigned_department || "Unassigned")}</td><td class="mono">${formatTime(c.created_at)}</td><td class="location">${formatLocation(c)}</td></tr>`).join("");
    body.querySelectorAll("tr").forEach((row) => row.addEventListener("click", () => onRowClick(row.dataset.id)));
  }
  function bindHeaders(onResort) { document.querySelectorAll(".queue__table th[data-sort]").forEach((th) => th.addEventListener("click", () => { setSort(th.dataset.sort); onResort(); })); }
  return { render, bindHeaders };
})();
