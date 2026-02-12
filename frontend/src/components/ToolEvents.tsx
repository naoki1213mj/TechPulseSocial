import { ChevronDown, ChevronRight, ClipboardCheck, FileSearch, Globe, ImageIcon, Pencil, Search, Wrench } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ToolEvent } from "../lib/api";

interface ToolEventsProps {
  events: ToolEvent[];
  t: (key: string) => string;
  isGenerating?: boolean;
}

/** Display config for each tool — icon is now a Lucide component */
const TOOL_CONFIG: Record<string, {
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
  category: string;
  gradient: string;      // running state gradient
  completedBg: string;   // completed state bg
}> = {
  web_search: {
    Icon: Globe,
    label: "Web Search",
    category: "search",
    gradient: "from-sky-500 to-blue-600",
    completedBg: "bg-sky-100 dark:bg-sky-900/40 text-sky-700 dark:text-sky-300 border-sky-300 dark:border-sky-700",
  },
  file_search: {
    Icon: FileSearch,
    label: "File Search",
    category: "search",
    gradient: "from-violet-500 to-purple-600",
    completedBg: "bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 border-violet-300 dark:border-violet-700",
  },
  generate_content: {
    Icon: Pencil,
    label: "Generate Content",
    category: "content",
    gradient: "from-emerald-500 to-teal-600",
    completedBg: "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700",
  },
  review_content: {
    Icon: ClipboardCheck,
    label: "Review Content",
    category: "review",
    gradient: "from-amber-500 to-orange-600",
    completedBg: "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-700",
  },
  generate_image: {
    Icon: ImageIcon,
    label: "Generate Image",
    category: "image",
    gradient: "from-pink-500 to-rose-600",
    completedBg: "bg-pink-100 dark:bg-pink-900/40 text-pink-700 dark:text-pink-300 border-pink-300 dark:border-pink-700",
  },
};

const DEFAULT_CONFIG = {
  Icon: Wrench,
  label: "Tool",
  category: "other",
  gradient: "from-gray-500 to-gray-600",
  completedBg: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-700",
};

export default function ToolEvents({
  events,
  t,
  isGenerating = false,
}: ToolEventsProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const prevCountRef = useRef(0);

  // Deduplicate: keep latest event per tool name
  const latestByTool = useMemo(() => {
    const map = new Map<string, ToolEvent>();
    events.forEach((ev) => map.set(ev.tool, ev));
    return Array.from(map.values());
  }, [events]);

  // Auto-flash when new tools appear
  useEffect(() => {
    if (latestByTool.length > prevCountRef.current) {
      prevCountRef.current = latestByTool.length;
    }
  }, [latestByTool.length]);

  // Sorted: running first, then completed
  const sorted = useMemo(() => {
    return [...latestByTool].sort((a, b) => {
      if (a.status === "started" && b.status !== "started") return -1;
      if (a.status !== "started" && b.status === "started") return 1;
      return 0;
    });
  }, [latestByTool]);

  if (sorted.length === 0 && !isGenerating) return null;

  // Show waiting state when generating but no tools yet
  if (sorted.length === 0 && isGenerating) {
    return (
      <div className="flex items-center gap-2 py-2 px-1">
        <Search className="w-3.5 h-3.5 text-gray-400 animate-pulse" />
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {t("tools.waiting") || "Analyzing..."}
        </span>
      </div>
    );
  }

  const runningCount = sorted.filter((e) => e.status === "started").length;
  const completedCount = sorted.filter((e) => e.status === "completed").length;

  return (
    <div className="tool-events-v2">
      {/* Always-visible tool pill bar */}
      <div className="flex flex-wrap items-center gap-2">
        {sorted.map((ev) => {
          const cfg = TOOL_CONFIG[ev.tool] ?? DEFAULT_CONFIG;
          const isRunning = ev.status === "started";
          const isError = ev.status === "error";
          const Icon = cfg.Icon;

          return (
            <div
              key={ev.tool}
              className={`tool-pill ${isRunning ? "tool-pill-running" : ""} ${isError ? "tool-pill-error" : ""}`}
            >
              {/* Animated gradient border for running state */}
              {isRunning && (
                <span className={`tool-pill-glow bg-gradient-to-r ${cfg.gradient}`} />
              )}

              <span className={`tool-pill-inner ${isRunning ? "" : cfg.completedBg}`}>
                <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${isRunning ? "animate-pulse" : ""}`} />
                <span className="tool-pill-label">{cfg.label}</span>
                <span className={`tool-pill-badge ${
                  isRunning ? "tool-badge-running" : isError ? "tool-badge-error" : "tool-badge-done"
                }`}>
                  {isRunning ? (
                    <span className="flex items-center gap-1">
                      <span className="tool-dot-pulse" />
                      {t("tools.started") || "Running"}
                    </span>
                  ) : isError ? (
                    t("tools.error") || "Error"
                  ) : (
                    <span>✓ {t("tools.completed") || "Done"}</span>
                  )}
                </span>
              </span>
            </div>
          );
        })}
      </div>

      {/* Summary + expand for details */}
      <div className="flex items-center gap-3 mt-1.5">
        <button
          onClick={() => setDetailsOpen(!detailsOpen)}
          className="tool-details-toggle"
          aria-expanded={detailsOpen}
        >
          {detailsOpen ? (
            <ChevronDown className="w-3 h-3" />
          ) : (
            <ChevronRight className="w-3 h-3" />
          )}
          <span className="text-[11px]">
            {completedCount > 0 && `${completedCount} ${t("tools.completed") || "done"}`}
            {runningCount > 0 && completedCount > 0 && " · "}
            {runningCount > 0 && `${runningCount} ${t("tools.started") || "running"}`}
          </span>
        </button>
      </div>

      {/* Expanded details panel */}
      {detailsOpen && (
        <div className="tool-details-panel animate-dropdown">
          {sorted.map((ev) => {
            const cfg = TOOL_CONFIG[ev.tool] ?? DEFAULT_CONFIG;
            const Icon = cfg.Icon;
            return (
              <div key={ev.tool} className="tool-detail-row">
                <Icon className="w-4 h-4 flex-shrink-0 text-gray-500 dark:text-gray-400" />
                <span className="font-medium text-gray-700 dark:text-gray-200 text-xs">
                  {cfg.label}
                </span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                  ev.status === "completed"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
                    : ev.status === "error"
                      ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                      : "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                }`}>
                  {t(`tools.${ev.status}`) || ev.status}
                </span>
                {ev.message && (
                  <span className="text-[10px] text-gray-400 dark:text-gray-500 truncate max-w-[200px]">
                    {ev.message}
                  </span>
                )}
                <span className="text-[10px] text-gray-300 dark:text-gray-600 ml-auto">
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
