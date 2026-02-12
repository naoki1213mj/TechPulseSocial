import { Check, Copy } from "lucide-react";
import { useMemo, useState } from "react";
import Markdown from "react-markdown";
import type { SafetyResult } from "../lib/api";
import ContentCards, { ABCompareCards, type ABStructuredOutput, type StructuredOutput } from "./ContentCards";

interface ContentDisplayProps {
  content: string;
  t: (key: string) => string;
  isGenerating: boolean;
  onRefine?: (platform: string, feedback: string) => void;
  safetyResult?: SafetyResult | null;
  imageMap?: Record<string, string>;
}

/**
 * Try to parse structured JSON output from the agent response.
 * The agent wraps JSON in ```json fences, or may return raw JSON.
 * Returns either StructuredOutput or ABStructuredOutput or null.
 */
function tryParseOutput(content: string): { type: "normal"; data: StructuredOutput } | { type: "ab"; data: ABStructuredOutput } | null {
  if (!content) return null;

  // Try to extract JSON from ```json ... ``` fences
  const fenceMatch = content.match(/```json\s*\n?([\s\S]*?)```/);
  const jsonStr = fenceMatch ? fenceMatch[1].trim() : content.trim();

  // Quick check — must look like JSON object
  if (!jsonStr.startsWith("{")) return null;

  try {
    const parsed = JSON.parse(jsonStr);
    // A/B comparison mode
    if (parsed.mode === "ab" && parsed.variant_a && parsed.variant_b) {
      return { type: "ab", data: parsed as ABStructuredOutput };
    }
    // Normal mode
    if (parsed.contents && Array.isArray(parsed.contents) && parsed.contents.length > 0) {
      return { type: "normal", data: parsed as StructuredOutput };
    }
  } catch {
    // Not valid JSON yet (might be streaming partial)
  }

  return null;
}

/**
 * Merge server-side extracted images into parsed structured output.
 * The imageMap keys are platform names (e.g. "linkedin", "x", "instagram").
 */
function mergeImages<T extends StructuredOutput | ABStructuredOutput>(
  data: T,
  imageMap: Record<string, string>,
): T {
  if (!imageMap || Object.keys(imageMap).length === 0) return data;

  if ("mode" in data && data.mode === "ab") {
    const ab = data as ABStructuredOutput;
    const merge = (contents: StructuredOutput["contents"]) =>
      contents.map((item) => {
        const key = item.platform?.toLowerCase() ?? "";
        return imageMap[key] ? { ...item, image_base64: imageMap[key] } : item;
      });
    return {
      ...ab,
      variant_a: { ...ab.variant_a, contents: merge(ab.variant_a.contents) },
      variant_b: { ...ab.variant_b, contents: merge(ab.variant_b.contents) },
    } as T;
  }

  const normal = data as StructuredOutput;
  return {
    ...normal,
    contents: normal.contents.map((item) => {
      const key = item.platform?.toLowerCase() ?? "";
      return imageMap[key] ? { ...item, image_base64: imageMap[key] } : item;
    }),
  } as T;
}

export default function ContentDisplay({
  content,
  t,
  isGenerating,
  onRefine,
  safetyResult,
  imageMap = {},
}: ContentDisplayProps) {
  const [copied, setCopied] = useState(false);

  // Try to parse structured output (normal or A/B)
  const parsed = useMemo(() => tryParseOutput(content), [content]);

  if (!content && !isGenerating) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  // If structured JSON was parsed successfully, show appropriate cards
  if (parsed && !isGenerating) {
    if (parsed.type === "ab") {
      const merged = mergeImages(parsed.data, imageMap);
      return <ABCompareCards data={merged} t={t} onRefine={onRefine} />;
    }
    const merged = mergeImages(parsed.data, imageMap);
    return <ContentCards data={merged} t={t} onRefine={onRefine} safetyResult={safetyResult} />;
  }

  // Detect if content looks like JSON output (hide raw JSON during streaming)
  const looksLikeJson = (() => {
    if (!content) return false;
    const trimmed = content.trim();
    // Check for ```json fences or raw JSON object
    return trimmed.startsWith("```json") || (trimmed.startsWith("{") && trimmed.includes('"contents"'));
  })();

  // During streaming, if content is JSON, show a generating skeleton instead of raw JSON
  if (isGenerating && looksLikeJson) {
    return (
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500" />
            </div>
            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
              {t("input.generating")}
            </span>
          </div>
          {/* Skeleton content cards */}
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <div className="skeleton h-5 w-5 rounded-full" />
                  <div className="skeleton h-4 w-24" />
                </div>
                <div className="skeleton h-3 w-full" />
                <div className="skeleton h-3 w-5/6" />
                <div className="skeleton h-3 w-4/6" />
                <div className="flex gap-2 mt-2">
                  <div className="skeleton h-5 w-16 rounded-full" />
                  <div className="skeleton h-5 w-20 rounded-full" />
                  <div className="skeleton h-5 w-14 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Fallback: show raw Markdown (during streaming or for non-JSON output)
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
      {/* Header with copy */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 dark:border-gray-800">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
          {isGenerating ? t("input.generating") : `${content.length.toLocaleString()} ${t("content.chars")}`}
        </span>
        <button
          onClick={handleCopy}
          disabled={!content}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-green-500" />
              {t("content.copied")}
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              {t("content.copy")}
            </>
          )}
        </button>
      </div>

      {/* Markdown content */}
      <div className="prose dark:prose-invert max-w-none px-5 py-4 text-sm">
        {content ? (
          <Markdown>{content}</Markdown>
        ) : isGenerating ? (
          <div className="space-y-3">
            <div className="skeleton h-4 w-3/4" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-5/6" />
            <div className="skeleton h-4 w-2/3" />
            <div className="flex items-center gap-2 mt-4 text-gray-400">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" style={{ animationDelay: "150ms" }} />
              <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" style={{ animationDelay: "300ms" }} />
              <span className="text-xs ml-1">{t("input.generating")}</span>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
