/**
 * Live interactive map of reported issues.
 * Markers are colour-coded by AI-inferred severity so priority areas
 * are visible at a glance, per the problem statement's "priority areas"
 * requirement.
 */
window.CivicPulseMap = (function () {
  let map = null;
  let markerLayer = null;
  let onSelect = null;

  const SEVERITY_COLOR = {
    Low: "#2E6B4C",
    Medium: "#B9791F",
    High: "#A6421F",
    Critical: "#8C2A2A",
  };

  function init(onSelectCallback) {
    onSelect = onSelectCallback;
    const cfg = window.CivicPulseConfig;

    map = L.map("map", { zoomControl: true }).setView(
      cfg.DEFAULT_MAP_CENTER,
      cfg.DEFAULT_MAP_ZOOM
    );

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    markerLayer = L.layerGroup().addTo(map);
  }

  function markerIcon(severity) {
    const color = SEVERITY_COLOR[severity] || SEVERITY_COLOR.Low;
    return L.divIcon({
      className: "",
      html: `<span style="
        display:block;width:14px;height:14px;border-radius:50%;
        background:${color};border:2px solid #fff;
        box-shadow:0 0 0 1px ${color};"></span>`,
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });
  }

  function render(complaints) {
    markerLayer.clearLayers();
    const withCoords = complaints.filter(
      (c) => typeof c.latitude === "number" && typeof c.longitude === "number"
    );

    withCoords.forEach((c) => {
      const marker = L.marker([c.latitude, c.longitude], {
        icon: markerIcon(c.ai_severity),
      });
      marker.bindTooltip(`${c.ai_category} · ${c.ai_severity}`, {
        direction: "top",
        offset: [0, -8],
      });
      marker.on("click", () => onSelect && onSelect(c.id));
      marker.addTo(markerLayer);
    });

    if (withCoords.length > 0) {
      const bounds = L.latLngBounds(withCoords.map((c) => [c.latitude, c.longitude]));
      map.fitBounds(bounds.pad(0.25), { maxZoom: 15 });
    }
  }

  function highlight(id, complaints) {
    const target = complaints.find((c) => c.id === id);
    if (target && typeof target.latitude === "number") {
      map.panTo([target.latitude, target.longitude]);
    }
  }

  return { init, render, highlight };
})();
