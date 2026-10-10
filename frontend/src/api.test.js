import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  api,
  clearStoredToken,
  request,
  storeToken,
} from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  clearStoredToken();
});

function response({ ok = true, status = 200, body = null } = {}) {
  return {
    ok,
    status,
    text: vi.fn().mockResolvedValue(body === null ? "" : JSON.stringify(body)),
  };
}

describe("FixFlow API client", () => {
  it("adds the session bearer token and JSON content type", async () => {
    storeToken("test-token");
    const fetchMock = vi.fn().mockResolvedValue(response({ body: { ok: true } }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      request("/api/example", {
        method: "POST",
        body: JSON.stringify({ value: "one" }),
      }),
    ).resolves.toEqual({ ok: true });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.get("Authorization")).toBe("Bearer test-token");
    expect(options.headers.get("Content-Type")).toBe("application/json");
  });

  it("clears the session and emits an unauthorized event for protected 401 responses", async () => {
    storeToken("expired-token");
    const unauthorized = vi.fn();
    window.addEventListener("fixflow:unauthorized", unauthorized);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response({ ok: false, status: 401, body: { detail: "Could not validate credentials." } }),
      ),
    );

    await expect(request("/api/auth/me")).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      message: "Could not validate credentials.",
    });
    expect(window.sessionStorage.getItem("fixflow_access_token")).toBeNull();
    expect(unauthorized).toHaveBeenCalledTimes(1);
    window.removeEventListener("fixflow:unauthorized", unauthorized);
  });

  it("preserves login errors without clearing the login request session", async () => {
    storeToken("existing-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response({ ok: false, status: 401, body: { detail: "Invalid email or password." } }),
      ),
    );

    await expect(api.login("wrong@example.test", "wrong-password")).rejects.toEqual(
      expect.objectContaining({ status: 401, message: "Invalid email or password." }),
    );
    expect(window.sessionStorage.getItem("fixflow_access_token")).toBe("existing-token");
  });

  it("turns network failures into an actionable ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(request("/api/dashboard")).rejects.toEqual(
      expect.objectContaining({
        name: "ApiError",
        status: 0,
        message: "The FixFlow API is unavailable. Check that the backend is running.",
      }),
    );
    await expect(request("/api/dashboard")).rejects.toBeInstanceOf(ApiError);
  });

  it("serializes report filters without sending empty values", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ body: { items: [] } }));
    vi.stubGlobal("fetch", fetchMock);

    await api.workOrderReport({ search: "pump repair", status: "", skip: 0, limit: 10 });

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://127.0.0.1:8000/api/reports/work-orders?search=pump+repair&skip=0&limit=10",
    );
  });
});
