const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/api/health"),
  overview: () => request("/api/overview"),
  safety: () => request("/api/safety/intelligence"),
  refreshSafety: () => request("/api/safety/refresh", { method: "POST" }),
  incidents: (limit = 100) => request(`/api/incidents?limit=${limit}`),
  createIncident: body => request("/api/incidents", { method: "POST", body: JSON.stringify(body) }),
  status: (id, body) => request(`/api/incidents/${id}/status`, { method: "PATCH", body: JSON.stringify(body) }),
  responders: () => request("/api/response/responders"),
  dispatch: id => request(`/api/response/dispatch/${id}`, { method: "POST" }),
  arrive: id => request(`/api/response/arrive/${id}`, { method: "POST" }),
  closeResponse: (id, outcome = "handled") => request(`/api/response/close/${id}`, { method: "POST", body: JSON.stringify({ outcome }) }),
  responseMetrics: () => request("/api/response/metrics"),
  routes: params => request(`/api/mobility/routes?${new URLSearchParams(params)}`),
  outcomes: () => request("/api/outcomes"),
  sos: body => request("/api/sos", { method: "POST", body: JSON.stringify(body) }),
  areas: () => request("/api/locations/areas"),
  dataEngineering: () => request("/api/data-engineering/summary"),
  runPipeline: () => request("/api/data-engineering/run-pipeline", { method: "POST" }),
  testRealtimePipeline: (sample) => request("/api/data-engineering/test-realtime", { method: "POST", body: JSON.stringify(sample || {}) }),
  pipelineStatus: () => request("/api/data-engineering/status"),
  datasets: () => request("/api/datasets"),
  datasetSummary: () => request("/api/datasets/summary"),
  telemetry: (incidentId) => request(incidentId ? `/api/response/telemetry/${incidentId}` : "/api/response/telemetry"),
  erssStatus: () => request("/api/erss/status"),
  erssCadStream: () => request("/api/erss/cad-stream"),
  transmitCad: (id) => request(`/api/erss/transmit/${id}`, { method: "POST" }),
  escalateIncident: (id, reason = "Patrol unit unacknowledged past SLA") => request(`/api/erss/escalate/${id}`, { method: "POST", body: JSON.stringify({ reason }) }),
  getEscalation: (id) => request(`/api/erss/escalate/${id}`),
};
export { API };
