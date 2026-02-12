/**
 * Tests for frontend/src/lib/api.ts — parseChunk function.
 */
import { describe, expect, it } from "vitest";
import { parseChunk } from "./api";

describe("parseChunk", () => {
  it("parses plain text as text", () => {
    const result = parseChunk("Hello world");
    expect(result.text).toBe("Hello world");
    expect(result.toolEvents).toEqual([]);
    expect(result.reasoning).toBeNull();
    expect(result.done).toBe(false);
    expect(result.error).toBeNull();
  });

  it("parses done signal", () => {
    const raw = JSON.stringify({ type: "done", thread_id: "abc-123" });
    const result = parseChunk(raw);
    expect(result.done).toBe(true);
    expect(result.threadId).toBe("abc-123");
  });

  it("parses error signal", () => {
    const raw = JSON.stringify({ error: "Rate limit exceeded" });
    const result = parseChunk(raw);
    expect(result.error).toBe("Rate limit exceeded");
    expect(result.done).toBe(false);
  });

  it("extracts tool events from markers", () => {
    const toolEvent = {
      type: "tool_event",
      tool: "web_search",
      status: "started",
      timestamp: "2025-01-01T00:00:00Z",
    };
    const raw = `__TOOL_EVENT__${JSON.stringify(toolEvent)}__END_TOOL_EVENT__`;
    const result = parseChunk(raw);
    expect(result.toolEvents).toHaveLength(1);
    expect(result.toolEvents[0].tool).toBe("web_search");
    expect(result.toolEvents[0].status).toBe("started");
    expect(result.text).toBe("");
  });

  it("extracts reasoning from markers", () => {
    const raw =
      "__REASONING_REPLACE__Step 1: Analyze the topic\nStep 2: Research trends__END_REASONING_REPLACE__";
    const result = parseChunk(raw);
    expect(result.reasoning).toContain("Step 1");
    expect(result.reasoning).toContain("Step 2");
    expect(result.text).toBe("");
  });

  it("parses reasoning_update JSON envelope", () => {
    const raw = JSON.stringify({
      type: "reasoning_update",
      reasoning: "Thinking about the topic...",
    });
    const result = parseChunk(raw);
    expect(result.reasoning).toBe("Thinking about the topic...");
  });

  it("extracts content from choices", () => {
    const raw = JSON.stringify({
      choices: [
        {
          messages: [{ role: "assistant", content: "Generated content here" }],
        },
      ],
      thread_id: "thread-1",
    });
    const result = parseChunk(raw);
    expect(result.text).toBe("Generated content here");
    expect(result.threadId).toBe("thread-1");
  });

  it("handles empty string", () => {
    const result = parseChunk("");
    expect(result.text).toBe("");
    expect(result.toolEvents).toEqual([]);
    expect(result.done).toBe(false);
  });

  it("handles whitespace-only", () => {
    const result = parseChunk("   ");
    expect(result.text).toBe("");
  });

  it("handles mixed tool event and text", () => {
    const toolEvent = {
      type: "tool_event",
      tool: "generate_content",
      status: "completed",
      timestamp: "2025-01-01T00:00:00Z",
    };
    const raw = `__TOOL_EVENT__${JSON.stringify(toolEvent)}__END_TOOL_EVENT__some remaining text`;
    const result = parseChunk(raw);
    expect(result.toolEvents).toHaveLength(1);
    expect(result.text).toBe("some remaining text");
  });

  it("handles malformed tool event JSON gracefully", () => {
    const raw = "__TOOL_EVENT__{invalid json}__END_TOOL_EVENT__";
    const result = parseChunk(raw);
    expect(result.toolEvents).toEqual([]);
    // Malformed is just skipped
  });

  it("handles multiple tool events", () => {
    const e1 = JSON.stringify({
      type: "tool_event",
      tool: "web_search",
      status: "started",
      timestamp: "t1",
    });
    const e2 = JSON.stringify({
      type: "tool_event",
      tool: "web_search",
      status: "completed",
      timestamp: "t2",
    });
    const raw = `__TOOL_EVENT__${e1}__END_TOOL_EVENT____TOOL_EVENT__${e2}__END_TOOL_EVENT__`;
    const result = parseChunk(raw);
    expect(result.toolEvents).toHaveLength(2);
    expect(result.toolEvents[0].status).toBe("started");
    expect(result.toolEvents[1].status).toBe("completed");
  });
});
