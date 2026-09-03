/**
 * Renders the four analytics charts from the currently filtered
 * complaint set: category mix, severity mix, status distribution,
 * and reports received per day.
 */
window.CivicPulseAnalytics = (function () {
  let charts = {};
  const PALETTE = ["#2E6B4C", "#B9791F", "#A6421F", "#8C2A2A", "#5B685F", "#6E9C82", "#D4A94F"];

  function destroy(key) {
    if (charts[key]) {
      charts[key].destroy();
      charts[key] = null;
    }
  }

  function countBy(items, key) {
    const counts = {};
    items.forEach((item) => {
      const v = item[key] || "Unspecified";
      counts[v] = (counts[v] || 0) + 1;
    });
    return counts;
  }

  function baseOptions(extra = {}) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      ...extra,
    };
  }

  function renderCategory(complaints) {
    destroy("category");
    const counts = countBy(complaints, "ai_category");
    const ctx = document.getElementById("chartCategory");
    charts.category = new Chart(ctx, {
      type: "bar",
      data: {
        labels: Object.keys(counts),
        datasets: [{ data: Object.values(counts), backgroundColor: "#2E6B4C", borderRadius: 2 }],
      },
      options: baseOptions({
        indexAxis: "y",
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
      }),
    });
  }

  function renderSeverity(complaints) {
    destroy("severity");
    const order = ["Low", "Medium", "High", "Critical"];
    const counts = countBy(complaints, "ai_severity");
    const labels = order.filter((s) => counts[s]);
    const colors = { Low: "#2E6B4C", Medium: "#B9791F", High: "#A6421F", Critical: "#8C2A2A" };
    const ctx = document.getElementById("chartSeverity");
    charts.severity = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{ data: labels.map((l) => counts[l]), backgroundColor: labels.map((l) => colors[l]) }],
      },
      options: baseOptions({ plugins: { legend: { display: true, position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } } }),
    });
  }

  function renderStatus(complaints) {
    destroy("status");
    const order = ["Pending", "Acknowledged", "In Progress", "Resolved"];
    const counts = countBy(complaints, "status");
    const labels = order.filter((s) => counts[s]).length ? order : Object.keys(counts);
    const ctx = document.getElementById("chartStatus");
    charts.status = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{ data: labels.map((l) => counts[l] || 0), backgroundColor: "#B9791F", borderRadius: 2 }],
      },
      options: baseOptions({ scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }),
    });
  }

  function renderTrend(complaints) {
    destroy("trend");
    const counts = {};
    complaints.forEach((c) => {
      if (!c.created_at) return;
      const day = new Date(c.created_at).toISOString().slice(0, 10);
      counts[day] = (counts[day] || 0) + 1;
    });
    const days = Object.keys(counts).sort();
    const ctx = document.getElementById("chartTrend");
    charts.trend = new Chart(ctx, {
      type: "line",
      data: {
        labels: days,
        datasets: [
          {
            data: days.map((d) => counts[d]),
            borderColor: "#2E6B4C",
            backgroundColor: "#E4EFE7",
            fill: true,
            tension: 0.25,
            pointRadius: 3,
          },
        ],
      },
      options: baseOptions({ scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }),
    });
  }

  function renderAll(complaints) {
    renderCategory(complaints);
    renderSeverity(complaints);
    renderStatus(complaints);
    renderTrend(complaints);
  }

  return { renderAll };
})();
