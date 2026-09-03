/**
 * Runtime configuration for CivicPulse.
 *
 * IMPORTANT:
 * Category, severity, status and department values here
 * must match the backend exactly.
 */

window.CivicPulseConfig = {
  get apiBase() {
    return (
      localStorage.getItem("cp_api_base") ||
      "http://localhost:8000"
    );
  },

  set apiBase(value) {
    localStorage.setItem(
      "cp_api_base",
      value.replace(/\/+$/, "")
    );
  },

  // -----------------------------------------------------
  // Canonical categories
  // -----------------------------------------------------

  CATEGORIES: [
    "Roads and Potholes",
    "Water Supply",
    "Electricity and Power",
    "Waste Management",
    "Public Safety",
    "Sanitation",
    "Traffic Issues",
  ],

  // -----------------------------------------------------
  // Severity
  // -----------------------------------------------------

  SEVERITIES: [
    "Low",
    "Medium",
    "High",
    "Critical",
  ],

  // -----------------------------------------------------
  // Complaint status
  // -----------------------------------------------------

  STATUSES: [
    "Pending",
    "Acknowledged",
    "In Progress",
    "Resolved",
  ],

  // -----------------------------------------------------
  // Departments
  // -----------------------------------------------------

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

  // -----------------------------------------------------
  // Map
  // -----------------------------------------------------

  DEFAULT_MAP_CENTER: [
    23.3441,
    85.3096,
  ],

  DEFAULT_MAP_ZOOM: 12,

  // -----------------------------------------------------
  // Refresh
  // -----------------------------------------------------

  REFRESH_INTERVAL_MS: 30000,
};