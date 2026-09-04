window.CivicPulseAPI = (function () {
  async function request(path, options = {}) {
    const base = window.CivicPulseConfig.apiBase;
    let response;
    try {
      response = await fetch(`${base}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      });
    } catch (error) {
      throw new Error(`Network error connecting to ${base}`);
    }
    if (!response.ok) {
      let detail = response.statusText || "Request failed";
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch (_) {}
      throw new Error(`${response.status} ${detail}`);
    }
    if (response.status === 204) return null;
    return response.json();
  }
  return {
    getComplaints() { return request("/api/complaints"); },
    getComplaint(id) { return request(`/api/complaints/${encodeURIComponent(id)}`); },
    updateComplaint(id, patch) {
      return request(`/api/complaints/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(patch) });
    },
  };
})();
