/** CivicPulse Ops runtime configuration. */
window.CivicPulseConfig = {
  get apiBase() {
    return localStorage.getItem("cp_api_base") || `${window.location.protocol}//${window.location.hostname}:8000`;
  },
  set apiBase(value) {
    localStorage.setItem("cp_api_base", String(value || "").replace(/\/+$/, ""));
  },
  CATEGORIES: [
    "Roads and Potholes", "Water Supply", "Electricity and Power",
    "Waste Management", "Public Safety", "Sanitation", "Traffic Issues",
  ],
  SEVERITIES: ["Low", "Medium", "High", "Critical"],
  STATUSES: ["Pending", "Acknowledged", "In Progress", "Resolved"],
  DEPARTMENTS: [
    "Unassigned", "Public Works Department (PWD)", "Water and Sewage Board",
    "Electricity Board", "Municipal Solid Waste Dept", "Local Police",
    "Health and Sanitation Dept", "Traffic Police", "City Municipal Corporation",
  ],
  DEFAULT_MAP_CENTER: [23.3441, 85.3096],
  DEFAULT_MAP_ZOOM: 13,
  REFRESH_INTERVAL_MS: 10000,
};
