window.CivicPulseAnalytics = (function () {
  let charts = {};
  function destroy(key) { if (charts[key]) { charts[key].destroy(); charts[key] = null; } }
  function countBy(items, key) { const counts = {}; items.forEach((item) => { const value = item[key] || "Unspecified"; counts[value] = (counts[value] || 0) + 1; }); return counts; }
  function baseOptions(extra = {}) { return { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, ...extra }; }
  
  function renderCategory(items) { destroy("category"); const counts = countBy(items, "ai_category"); const ctx = document.getElementById("chartCategory"); if (!ctx) return; charts.category = new Chart(ctx, { type: "bar", data: { labels: Object.keys(counts), datasets: [{ data: Object.values(counts), backgroundColor: "#0f172a", borderRadius: 4 }] }, options: baseOptions({ indexAxis: "y", scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } }) }); }
  function renderSeverity(items) { destroy("severity"); const order = ["Low", "Medium", "High", "Critical"]; const counts = countBy(items, "ai_severity"); const labels = order.filter((value) => counts[value]); const colors = { Low: "#10b981", Medium: "#f59e0b", High: "#f97316", Critical: "#ef4444" }; const ctx = document.getElementById("chartSeverity"); if (!ctx) return; charts.severity = new Chart(ctx, { type: "doughnut", data: { labels, datasets: [{ data: labels.map((label) => counts[label]), backgroundColor: labels.map((label) => colors[label]), borderWidth: 0 }] }, options: baseOptions({ plugins: { legend: { display: true, position: "bottom", labels: { boxWidth: 10, font: { size: 12, family: "'Inter', sans-serif" } } } } }) }); }
  function renderStatus(items) { destroy("status"); const order = ["Pending", "Acknowledged", "In Progress", "Resolved"]; const counts = countBy(items, "status"); const labels = order.filter((value) => counts[value]).length ? order : Object.keys(counts); const ctx = document.getElementById("chartStatus"); if (!ctx) return; charts.status = new Chart(ctx, { type: "bar", data: { labels, datasets: [{ data: labels.map((label) => counts[label] || 0), backgroundColor: "#3b82f6", borderRadius: 4 }] }, options: baseOptions({ scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }) }); }
  
  function renderDepartment(items) { 
    destroy("department"); 
    const counts = countBy(items.filter(item => item.status !== 'Resolved'), "assigned_department"); 
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 3);
    const labels = sorted.map(i => i[0]);
    const data = sorted.map(i => i[1]);
    const ctx = document.getElementById("chartDepartment"); 
    if (!ctx) return; 
    charts.department = new Chart(ctx, { 
      type: "bar", 
      data: { labels, datasets: [{ data, backgroundColor: ["#ef4444", "#f97316", "#f59e0b"], borderRadius: 4 }] }, 
      options: baseOptions({ indexAxis: "x", scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }) 
    }); 
  }
  
  function renderTrend(items) { destroy("trend"); const counts = {}; items.forEach((item) => { if (!item.created_at) return; const day = new Date(item.created_at).toLocaleDateString(); counts[day] = (counts[day] || 0) + 1; }); const days = Object.keys(counts).sort((a, b) => new Date(a) - new Date(b)); const ctx = document.getElementById("chartTrend"); if (!ctx) return; charts.trend = new Chart(ctx, { type: "line", data: { labels: days, datasets: [{ data: days.map((day) => counts[day]), borderColor: "#0f172a", backgroundColor: "rgba(15, 23, 42, 0.05)", fill: true, tension: 0.3, pointRadius: 4, pointBackgroundColor: "#0f172a" }] }, options: baseOptions({ scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }) }); }
  
  function renderAll(items) { renderCategory(items); renderSeverity(items); renderStatus(items); renderDepartment(items); renderTrend(items); }
  return { renderAll };
})();
