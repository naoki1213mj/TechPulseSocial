/** API client for the TechPulse Social backend */

export interface ChatRequest {
  message: string;
  thread_id?: string;
  platforms: string[];
  content_type: string;
  language: string;
  reasoning_effort: string;
  reasoning_summary: string;
  ab_mode?: boolean;
}

export interface ToolEvent {
  type: "tool_event";
  tool: string;
  status: "started" | "completed" | "error";
  timestamp: string;
  message?: string;
}

export interface SafetyResult {
  safe: boolean;
  skipped?: boolean;
  reason?: string;
  categories?: Record<string, number>;
  blocked_categories?: string[];
  summary?: string;
}

export interface ChatChunk {
  choices?: Array<{
    messages: Array<{ role: string; content: string }>;
  }>;
  thread_id?: string;
  type?: "done" | "error" | "reasoning_update" | "safety";
  reasoning?: string;
  error?: string;
  message?: string;
  safety?: SafetyResult;
  summary?: string;
}

// SSE marker patterns (matching backend)
const TOOL_EVENT_RE =
  /__TOOL_EVENT__([\s\S]*?)__END_TOOL_EVENT__/g;
const REASONING_RE =
  /__REASONING_REPLACE__([\s\S]*?)__END_REASONING_REPLACE__/g;

export interface ParsedChunk {
  text: string;
  toolEvents: ToolEvent[];
  reasoning: string | null;
  done: boolean;
  threadId: string | null;
  error: string | null;
  safety: SafetyResult | null;
}

/**
 * Parse a raw SSE chunk into structured data.
 */
export function parseChunk(raw: string): ParsedChunk {
  const toolEvents: ToolEvent[] = [];
  let reasoning: string | null = null;
  let cleaned = raw;

  // Extract tool events
  for (const m of raw.matchAll(TOOL_EVENT_RE)) {
    try {
      toolEvents.push(JSON.parse(m[1]));
    } catch { /* skip malformed */ }
    cleaned = cleaned.replace(m[0], "");
  }

  // Extract reasoning (REPLACE mode — full cumulative text)
  for (const m of raw.matchAll(REASONING_RE)) {
    reasoning = m[1];
    cleaned = cleaned.replace(m[0], "");
  }

  // Try to parse remaining as JSON
  cleaned = cleaned.trim();
  if (!cleaned) {
    return { text: "", toolEvents, reasoning, done: false, threadId: null, error: null, safety: null };
  }

  try {
    const obj: ChatChunk = JSON.parse(cleaned);
    if (obj.type === "done") {
      return { text: "", toolEvents, reasoning, done: true, threadId: obj.thread_id ?? null, error: null, safety: null };
    }
    // Safety result from Content Safety analysis
    if (obj.type === "safety" && obj.safety) {
      return { text: "", toolEvents, reasoning, done: false, threadId: null, error: null, safety: obj.safety as SafetyResult };
    }
    // Reasoning delivered as JSON envelope (avoids \n\n SSE framing issues)
    if (obj.type === "reasoning_update" && obj.reasoning) {
      return { text: "", toolEvents, reasoning: obj.reasoning, done: false, threadId: null, error: null, safety: null };
    }
    if (obj.error) {
      return { text: "", toolEvents, reasoning, done: false, threadId: null, error: obj.error, safety: null };
    }
    const content = obj.choices?.[0]?.messages?.[0]?.content ?? "";
    const threadId = obj.thread_id ?? null;
    return { text: content, toolEvents, reasoning, done: false, threadId, error: null, safety: null };
  } catch {
    // Not JSON — treat as plain text
    return { text: cleaned, toolEvents, reasoning, done: false, threadId: null, error: null, safety: null };
  }
}

/**
 * Stream a chat request via fetch + ReadableStream.
 */
export async function* streamChat(
  req: ChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<ParsedChunk> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder("utf-8");

  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE chunks are separated by double newlines
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const trimmed = part.trim();
      if (!trimmed) continue;
      yield parseChunk(trimmed);
    }
  }

  // Process remaining buffer
  if (buffer.trim()) {
    yield parseChunk(buffer.trim());
  }
}
