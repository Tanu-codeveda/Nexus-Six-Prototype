/**
 * API client for the CivicPulse Core API (main.py).
 * Talks to:
 *   GET   /api/complaints
 *   GET   /api/complaints/{id}
 *   PATCH /api/complaints/{id}   { status?, assigned_department? }
 */
window.CivicPulseAPI = (function () {
  async function request(path, options = {}) {
    const base = window.CivicPulseConfig.apiBase;
    const res = await fetch(`${base}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch (_) {}
      throw new Error(`${res.status} ${detail}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  return {
    getComplaints() {
      return request("/api/complaints");
    },
    getComplaint(id) {
      return request(`/api/complaints/${id}`);
    },
    updateComplaint(id, patch) {
      return request(`/api/complaints/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
    },
  };
})();
