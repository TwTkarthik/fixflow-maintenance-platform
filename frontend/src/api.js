const apiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export const API_BASE_URL = apiBaseUrl;
export const TOKEN_STORAGE_KEY = "fixflow_access_token";

export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export function getStoredToken() {
  return window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

export function storeToken(token) {
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken() {
  window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
}

function messageFromDetails(details, fallback) {
  if (typeof details === "string") return details;
  if (Array.isArray(details)) {
    return details.map((item) => item?.msg || item?.detail || String(item)).join(" ");
  }
  if (details && typeof details.detail === "string") return details.detail;
  return fallback;
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getStoredToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  let response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers });
  } catch (error) {
    throw new ApiError("The FixFlow API is unavailable. Check that the backend is running.", 0, error);
  }

  const raw = await response.text();
  let data = null;
  if (raw) {
    try { data = JSON.parse(raw); } catch { data = raw; }
  }
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/auth/login") {
      clearStoredToken();
      window.dispatchEvent(new Event("fixflow:unauthorized"));
    }
    throw new ApiError(messageFromDetails(data, `The API returned HTTP ${response.status}.`), response.status, data);
  }
  return data;
}

function query(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  });
  return search.toString();
}

export const api = {
  login: (email, password) => request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request("/api/auth/me"),
  dashboard: (params = {}) => request(`/api/dashboard?${query(params)}`),
  assets: (params = {}) => request(`/api/assets?${query(params)}`),
  asset: (id) => request(`/api/assets/${id}`),
  assetHistory: (id) => request(`/api/assets/${id}/maintenance-history`),
  createAsset: (payload) => request("/api/assets", { method: "POST", body: JSON.stringify(payload) }),
  updateAsset: (id, payload) => request(`/api/assets/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deactivateAsset: (id) => request(`/api/assets/${id}/deactivate`, { method: "POST" }),
  workOrders: (params = {}) => request(`/api/work-orders?${query(params)}`),
  workOrder: (id) => request(`/api/work-orders/${id}`),
  createWorkOrder: (payload) => request("/api/work-orders", { method: "POST", body: JSON.stringify(payload) }),
  updateWorkOrder: (id, payload) => request(`/api/work-orders/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  assignWorkOrder: (id, technicianId) => request(`/api/work-orders/${id}/assign`, { method: "POST", body: JSON.stringify({ technician_id: Number(technicianId) }) }),
  changeStatus: (id, payload) => request(`/api/work-orders/${id}/status`, { method: "POST", body: JSON.stringify(payload) }),
  addNote: (id, note) => request(`/api/work-orders/${id}/notes`, { method: "POST", body: JSON.stringify({ note }) }),
  history: (id) => request(`/api/work-orders/${id}/history`),
  maintenance: (id) => request(`/api/work-orders/${id}/maintenance`),
  workOrderReport: (params = {}) => request(`/api/reports/work-orders?${query(params)}`),
  maintenanceReport: (params = {}) => request(`/api/reports/maintenance?${query(params)}`),
};
