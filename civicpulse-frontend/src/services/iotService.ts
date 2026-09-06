const API_BASE = '/api/iot';

export const iotService = {
  runBinCheck: async () => {
    const res = await fetch(`${API_BASE}/run-bin-check`, { method: 'POST' });
    return res.json();
  },
  runPotholeCheck: async () => {
    const res = await fetch(`${API_BASE}/run-pothole-check`, { method: 'POST' });
    return res.json();
  },
  runStreetlightCheck: async () => {
    const res = await fetch(`${API_BASE}/run-streetlight-check`, { method: 'POST' });
    return res.json();
  },
  checkDrain: async (zoneId: string) => {
    const res = await fetch(`${API_BASE}/check-drain/${zoneId}`, { method: 'POST' });
    return res.json();
  }
};
