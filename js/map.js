window.CivicPulseMap = (function () {
  let map = null;
  let markerLayer = null;
  let hotspotLayer = null;
  let onSelect = null;
  const SEVERITY_COLOR = { Low: "#2E6B4C", Medium: "#B9791F", High: "#A6421F", Critical: "#8C2A2A" };

  function init(onSelectCallback) {
    onSelect = onSelectCallback;
    const cfg = window.CivicPulseConfig;
    map = L.map("map", { zoomControl: true }).setView(cfg.DEFAULT_MAP_CENTER, cfg.DEFAULT_MAP_ZOOM);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(map);
    markerLayer = L.layerGroup().addTo(map);
    hotspotLayer = L.layerGroup().addTo(map);
  }

  function markerIcon(severity) {
    const color = SEVERITY_COLOR[severity] || SEVERITY_COLOR.Low;
    return L.divIcon({ className: "", html: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 0 1px ${color};"></span>`, iconSize: [14, 14], iconAnchor: [7, 7] });
  }

  function distanceKm(a, b) {
    const R = 6371;
    const dLat = (b.latitude - a.latitude) * Math.PI / 180;
    const dLon = (b.longitude - a.longitude) * Math.PI / 180;
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.latitude * Math.PI / 180) * Math.cos(b.latitude * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  function renderHotspots(items) {
    hotspotLayer.clearLayers();
    const visited = new Set();
    const groups = [];
    items.forEach((seed) => {
      if (visited.has(seed.id)) return;
      const group = items.filter((item) => item.id !== seed.id && !visited.has(item.id) && item.ai_category === seed.ai_category && distanceKm(seed, item) <= 0.65);
      const all = [seed, ...group];
      all.forEach((item) => visited.add(item.id));
      if (all.length >= 3) groups.push(all);
    });
    groups.forEach((group) => {
      const lat = group.reduce((sum, item) => sum + item.latitude, 0) / group.length;
      const lon = group.reduce((sum, item) => sum + item.longitude, 0) / group.length;
      const high = group.filter((item) => item.ai_severity === "High" || item.ai_severity === "Critical").length;
      const radius = Math.min(700, 240 + group.length * 60);
      const color = high >= 2 ? "#8C2A2A" : "#B9791F";
      L.circle([lat, lon], { radius, color, fillColor: color, fillOpacity: 0.15, weight: 2 })
        .bindPopup(`<strong>Priority hotspot</strong><br>${group.length} related ${group[0].ai_category} reports within ~650 m<br>${high} high/critical`)
        .addTo(hotspotLayer);
    });
  }

  function render(complaints) {
    markerLayer.clearLayers();
    hotspotLayer.clearLayers();
    const withCoords = complaints.filter((c) => typeof c.latitude === "number" && typeof c.longitude === "number");
    withCoords.forEach((c) => {
      L.marker([c.latitude, c.longitude], { icon: markerIcon(c.ai_severity) })
        .bindTooltip(`${c.ai_category || "General Maintenance"} · ${c.ai_severity || "Low"}`, { direction: "top", offset: [0, -8] })
        .on("click", () => onSelect && onSelect(c.id))
        .addTo(markerLayer);
    });
    renderHotspots(withCoords);

    const cfg = window.CivicPulseConfig;
    const local = withCoords.filter((c) => Math.abs(c.latitude - cfg.DEFAULT_MAP_CENTER[0]) <= 0.15 && Math.abs(c.longitude - cfg.DEFAULT_MAP_CENTER[1]) <= 0.15);
    if (local.length > 0) {
      map.fitBounds(L.latLngBounds(local.map((c) => [c.latitude, c.longitude])).pad(0.20), { maxZoom: 14 });
    } else {
      map.setView(cfg.DEFAULT_MAP_CENTER, cfg.DEFAULT_MAP_ZOOM);
    }
  }

  function highlight(id, complaints) {
    const target = complaints.find((c) => c.id === id);
    if (target && typeof target.latitude === "number") map.panTo([target.latitude, target.longitude]);
  }
  return { init, render, highlight };
})();
