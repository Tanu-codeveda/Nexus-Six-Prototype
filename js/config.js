/**
 * Runtime configuration.
 * Backend is the FastAPI service from main.py (Member 3's Core API).
 * Change the API base at runtime via the ⚙ settings drawer — it is
 * persisted in localStorage so each admin only sets it once per browser.
 */
window.CivicPulseConfig = {
  get apiBase() {
    return localStorage.getItem("cp_api_base") || "http://localhost:8000";
  },
  set apiBase(value) {
    localStorage.setItem("cp_api_base", value.replace(/\/+$/, ""));
  },

  // Taxonomies mirrored from ai_helpers.py so filters/selects work even
  // before the AI/ML services are wired up.
  CATEGORIES: [
    "Roads and Potholes",
    "Water Supply",
    "Electricity and Power",
    "Waste Management",
    "Public Safety",
    "Sanitation",
    "Traffic Issues",
  ],
  SEVERITIES: ["Low", "Medium", "High", "Critical"],
  STATUSES: ["Pending", "Acknowledged", "In Progress", "Resolved"],
  DEPARTMENTS: [
    "Unassigned",
    "Public Works Department (PWD)",
    "Water and Sewage Board",
    "Electricity Board",
    "Municipal Solid Waste Dept",
    "Local Police",
    "Health and Sanitation Dept",
    "Traffic Police",
    "City Municipal Corporation",
  ],

  // Fallback map center: Ranchi, Jharkhand.
  DEFAULT_MAP_CENTER: [23.3441, 85.3096],
  DEFAULT_MAP_ZOOM: 12,

  REFRESH_INTERVAL_MS: 30000,
};
