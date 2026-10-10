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

    fireEvent.click(screen.getByRole("button", { name: "Maintenance report" }));
    expect(await screen.findByText("No report data")).toBeTruthy();
    expect(mockApi.maintenanceReport).toHaveBeenCalled();
  });

  it("shows an actionable error when the maintenance report request fails", async () => {
    arrangeAuthenticated();
    mockApi.workOrderReport.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 10 });
    mockApi.maintenanceReport.mockRejectedValue(new Error("Maintenance report unavailable"));

    render(<App />);
    await screen.findByRole("heading", { name: /here's the pulse/i });
    fireEvent.click(screen.getByRole("link", { name: /reports/i }));
    await screen.findByText("No report data");
    fireEvent.click(screen.getByRole("button", { name: "Maintenance report" }));

    expect(await screen.findByText("Maintenance report unavailable")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  });

  it("renders a completed maintenance record from the maintenance report response", async () => {
    arrangeAuthenticated();
    mockApi.workOrderReport.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 10 });
    mockApi.maintenanceReport.mockResolvedValue({
      items: [{
        id: 1,
        asset_id: 1,
        asset_code: "PUMP-001",
        asset_name: "North Plant Pump",
        work_order_id: 1,
        performed_by_id: 2,
        performed_by: { id: 2, full_name: "Tariq Technician", email: "tech@example.test", role: "technician" },
        outcome: "Pump repaired",
        work_performed: "Replaced the worn seal.",
        completed_at: "2026-10-10T10:30:00Z",
        created_at: "2026-10-10T10:30:00Z",
      }],
      total: 1,
      skip: 0,
      limit: 10,
    });

    render(<App />);
    await screen.findByRole("heading", { name: /here's the pulse/i });
    fireEvent.click(screen.getByRole("link", { name: /reports/i }));
    await screen.findByText("No report data");
    fireEvent.click(screen.getByRole("button", { name: "Maintenance report" }));

    expect(await screen.findByText("WO-0001")).toBeTruthy();
    expect(screen.getByText("North Plant Pump")).toBeTruthy();
    expect(screen.getByText("Tariq Technician")).toBeTruthy();
    expect(screen.getByRole("cell", { name: "Oct 10, 2026" })).toBeTruthy();
    expect(screen.getByText("Pump repaired")).toBeTruthy();
  });

  it("does not blank the page when a maintenance row has no technician summary", async () => {
    arrangeAuthenticated();
    mockApi.workOrderReport.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 10 });
    mockApi.maintenanceReport.mockResolvedValue({
      items: [{
        id: 1,
        asset_id: 1,
        asset_code: "PUMP-001",
        asset_name: "North Plant Pump",
        work_order_id: 1,
        performed_by_id: 2,
        performed_by: null,
        outcome: "Pump repaired",
        work_performed: "Replaced the worn seal.",
        completed_at: "2026-10-10T10:30:00Z",
        created_at: "2026-10-10T10:30:00Z",
      }],
      total: 1,
      skip: 0,
      limit: 10,
    });

    render(<App />);
    await screen.findByRole("heading", { name: /here's the pulse/i });
    fireEvent.click(screen.getByRole("link", { name: /reports/i }));
    await screen.findByText("No report data");
    fireEvent.click(screen.getByRole("button", { name: "Maintenance report" }));

    expect(await screen.findByText("Unknown technician")).toBeTruthy();
    expect(screen.getByText("North Plant Pump")).toBeTruthy();
  });

  it("shows the loading state while the maintenance report request is pending", async () => {
    arrangeAuthenticated();
    mockApi.workOrderReport.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 10 });
    let resolveMaintenance;
    mockApi.maintenanceReport.mockReturnValue(new Promise((resolve) => {
      resolveMaintenance = resolve;
    }));

    render(<App />);
    await screen.findByRole("heading", { name: /here's the pulse/i });
    fireEvent.click(screen.getByRole("link", { name: /reports/i }));
    await screen.findByText("No report data");
    fireEvent.click(screen.getByRole("button", { name: "Maintenance report" }));

    expect(screen.getByText("Loading report…")).toBeTruthy();
    resolveMaintenance({ items: [], total: 0, skip: 0, limit: 10 });
    expect(await screen.findByText("No report data")).toBeTruthy();
  });
});
