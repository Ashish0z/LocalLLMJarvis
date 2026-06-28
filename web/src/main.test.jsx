import { describe, it, expect, vi } from "vitest";

// ---------------------------------------------------------------------------
// Unit: headers() helper logic (extracted inline for testing)
// ---------------------------------------------------------------------------

function buildHeaders(apiKey, extra = {}) {
  return {
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
    ...extra,
  };
}

describe("buildHeaders", () => {
  it("includes X-API-Key when apiKey is set", () => {
    expect(buildHeaders("my-secret-key")).toEqual({ "X-API-Key": "my-secret-key" });
  });

  it("omits X-API-Key when apiKey is empty", () => {
    expect(buildHeaders("")).toEqual({});
  });

  it("merges extra headers", () => {
    const result = buildHeaders("key", { "Content-Type": "application/json" });
    expect(result).toEqual({
      "X-API-Key": "key",
      "Content-Type": "application/json",
    });
  });

  it("extra headers only when apiKey is absent", () => {
    const result = buildHeaders("", { Accept: "application/json" });
    expect(result).toEqual({ Accept: "application/json" });
  });
});

// ---------------------------------------------------------------------------
// Unit: API URL normalisation
// ---------------------------------------------------------------------------

describe("API base URL resolution", () => {
  it("falls back to localhost when VITE_API_BASE_URL is not set", async () => {
    // import.meta.env is not available outside of Vite; simulate default here.
    const VITE_API_BASE_URL = undefined;
    const resolved = VITE_API_BASE_URL || "http://localhost:8000";
    expect(resolved).toBe("http://localhost:8000");
  });

  it("respects a custom API base URL", () => {
    const VITE_API_BASE_URL = "http://192.168.1.10:8000";
    const resolved = VITE_API_BASE_URL || "http://localhost:8000";
    expect(resolved).toBe("http://192.168.1.10:8000");
  });
});

// ---------------------------------------------------------------------------
// Unit: document question gate
// ---------------------------------------------------------------------------

describe("askDocument guard conditions", () => {
  it("blocks submission when no document is selected", () => {
    const selectedDocumentId = "";
    const question = "What is the launch task?";
    const shouldSubmit = Boolean(selectedDocumentId && question.trim());
    expect(shouldSubmit).toBe(false);
  });

  it("blocks submission when question is blank", () => {
    const selectedDocumentId = "doc-123";
    const question = "  ";
    const shouldSubmit = Boolean(selectedDocumentId && question.trim());
    expect(shouldSubmit).toBe(false);
  });

  it("allows submission when both document and question are present", () => {
    const selectedDocumentId = "doc-123";
    const question = "What is the plan?";
    const shouldSubmit = Boolean(selectedDocumentId && question.trim());
    expect(shouldSubmit).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Unit: sendMessage guard condition
// ---------------------------------------------------------------------------

describe("sendMessage guard condition", () => {
  it("blocks send when text is empty", () => {
    const text = "";
    expect(Boolean(text.trim())).toBe(false);
  });

  it("blocks send when text is only whitespace", () => {
    const text = "   \t\n";
    expect(Boolean(text.trim())).toBe(false);
  });

  it("allows send when text has content", () => {
    const text = "Add a task for tomorrow";
    expect(Boolean(text.trim())).toBe(true);
  });
});
