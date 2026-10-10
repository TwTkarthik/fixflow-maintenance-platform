import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockApi = vi.hoisted(() => ({
  login: vi.fn(),
  me: vi.fn(),
  dashboard: vi.fn(),
  assets: vi.fn(),
  workOrders: vi.fn(),
  workOrderReport: vi.fn(),
  maintenanceReport: vi.fn(),
}));

vi.mock("./api", () => ({
  api: mockApi,
  API_BASE_URL: "http://127.0.0.1:8000",
  TOKEN_STORAGE_KEY: "fixflow_access_token",
  getStoredToken: () => window.sessionStorage.getItem("fixflow_access_token"),
  storeToken: (token) => window.sessionStorage.setItem("fixflow_access_token", token),
  clearStoredToken: () => window.sessionStorage.removeItem("fixflow_access_token"),
  ApiError: class ApiError extends Error {},
}));

import App from "./App";

const profiles = {
  manager: { id: 1, full_name: "Mina Manager", email: "manager@example.test", role: "manager", is_active: true },
  technician: { id: 2, full_name: "Tariq Technician", email: "tech@example.test", role: "technician", is_active: true },
};

const emptyDashboard = {
  total_assets: 0, active_assets: 0, deactivated_assets: 0, total_work_orders: 0,
  outstanding_work_orders: 0, overdue_work_orders: 0, completed_work_orders: 0,
  status_counts: [{ value: "open", count: 0 }, { value: "assigned", count: 0 }, { value: "in_progress", count: 0 }, { value: "on_hold", count: 0 }, { value: "completed", count: 0 }, { value: "cancelled", count: 0 }],
  priority_counts: [{ value: "low", count: 0 }, { value: "medium", count: 0 }, { value: "high", count: 0 }, { value: "critical", count: 0 }],
  total_maintenance_records: 0, assets_needing_attention: 0,
};

function arrangeAuthenticated(profile = profiles.manager) {
  window.sessionStorage.setItem("fixflow_access_token", "test-token");
  mockApi.me.mockResolvedValue(profile);
  mockApi.dashboard.mockResolvedValue(emptyDashboard);
  mockApi.assets.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 10 });
  mockApi.workOrders.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 10 });
}

describe("FixFlow application smoke coverage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/");
  });

  it("renders the sign-in screen without a session", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /run a tighter operation/i })).toBeTruthy();
    expect(screen.getByLabelText("Work email")).toBeTruthy();
  });

  it("shows the backend credential error for invalid login", async () => {
    mockApi.login.mockRejectedValue(new Error("Invalid email or password."));
    render(<App />);
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "wrong@example.test" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong-password" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText("Sign in failed. Try again.")).toBeTruthy();
  });

  it("restores a session and renders zero-safe dashboard data", async () => {
    arrangeAuthenticated();
    render(<App />);
    expect(await screen.findByRole("heading", { name: /here's the pulse/i })).toBeTruthy();
    expect(screen.queryByText("The queue is clear")).toBeNull();
    expect(mockApi.dashboard).toHaveBeenCalledWith({ date_from: "", date_to: "" });
  });

  it("shows an actionable dashboard error when the API request fails", async () => {
    arrangeAuthenticated();
    mockApi.dashboard.mockRejectedValue(new Error("Dashboard unavailable"));
    render(<App />);
    expect(await screen.findByText("Dashboard unavailable")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  });

  it("returns to sign in when session restoration rejects the token", async () => {
    window.sessionStorage.setItem("fixflow_access_token", "expired-token");
    mockApi.me.mockRejectedValue(new Error("Unauthorized"));
    render(<App />);
    expect(await screen.findByRole("heading", { name: /run a tighter operation/i })).toBeTruthy();
    expect(window.sessionStorage.getItem("fixflow_access_token")).toBeNull();
  });

  it("shows manager equipment controls but hides them for technicians", async () => {
    arrangeAuthenticated(profiles.manager);
    const firstRender = render(<App />);
    await screen.findByRole("heading", { name: /here's the pulse/i });
    fireEvent.click(screen.getByRole("link", { name: /Equipment/ }));
    expect(await screen.findByRole("button", { name: /add equipment/i })).toBeTruthy();
    firstRender.unmount();

    window.history.pushState({}, "", "/");
    arrangeAuthenticated(profiles.technician);
    render(<App />);
    await screen.findByRole("heading", { name: /here's the pulse/i });
    fireEvent.click(screen.getByRole("link", { name: /Equipment/ }));
    await waitFor(() => expect(screen.queryByRole("button", { name: /add equipment/i })).toBeNull());
  });

  it("loads the empty work-order and report states through protected navigation", async () => {
    arrangeAuthenticated();
    mockApi.workOrderReport.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 10 });
    mockApi.maintenanceReport.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 10 });
    render(<App />);
    await screen.findByRole("heading", { name: /here's the pulse/i });

    fireEvent.click(screen.getByRole("link", { name: /work orders/i }));
    expect(await screen.findByText("The queue is clear")).toBeTruthy();
    expect(mockApi.workOrders).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("link", { name: /reports/i }));
    expect(await screen.findByText("No report data")).toBeTruthy();
    expect(mockApi.workOrderReport).toHaveBeenCalled();
  });
});
