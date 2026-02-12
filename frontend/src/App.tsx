import { useCallback, useEffect, useRef, useState } from "react";
import ContentDisplay from "./components/ContentDisplay";
import Header from "./components/Header";
import HistorySidebar from "./components/HistorySidebar";
import InputForm from "./components/InputForm";
import ReasoningPanel from "./components/ReasoningPanel";
import SuggestedQuestions from "./components/SuggestedQuestions";
import ToolEvents from "./components/ToolEvents";
import { useI18n } from "./hooks/useI18n";
import { useTheme } from "./hooks/useTheme";
import { streamChat, type ToolEvent } from "./lib/api";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { locale, setLocale, t, toggleLocale } = useI18n("ja");

  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [suggestedTopic, setSuggestedTopic] = useState<string>("");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [lastSubmitData, setLastSubmitData] = useState<Parameters<typeof handleSubmit>[0] | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  // Elapsed time ticker
  useEffect(() => {
    if (loading) {
      startTimeRef.current = Date.now();
      setElapsedMs(0);
      timerRef.current = setInterval(() => {
        setElapsedMs(Date.now() - startTimeRef.current);
      }, 100);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [loading]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  const handleNewConversation = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
    setContent("");
    setReasoning("");
    setToolEvents([]);
    setThreadId(null);
    setError(null);
    setElapsedMs(0);
    setLastSubmitData(null);
  }, []);

  const handleSubmit = useCallback(
    async (data: {
      message: string;
      platforms: string[];
      contentType: string;
      language: string;
      reasoningEffort: string;
      reasoningSummary: string;
    }) => {
      // Save for retry
      setLastSubmitData(data);

      // Abort any in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      // Reset state
      setLoading(true);
      setContent("");
      setReasoning("");
      setToolEvents([]);
      setError(null);

      try {
        for await (const chunk of streamChat(
          {
            message: data.message,
            thread_id: threadId ?? undefined,
            platforms: data.platforms,
            content_type: data.contentType,
            language: data.language,
            reasoning_effort: data.reasoningEffort,
            reasoning_summary: data.reasoningSummary,
          },
          controller.signal,
        )) {
          // Reasoning — REPLACE mode (backend sends cumulative)
          if (chunk.reasoning !== null) {
            setReasoning(chunk.reasoning);
          }

          // Tool events — append
          if (chunk.toolEvents.length > 0) {
            setToolEvents((prev) => [...prev, ...chunk.toolEvents]);
          }

          // Text content — replace (backend sends cumulative content)
          if (chunk.text) {
            setContent(chunk.text);
          }

          // Thread ID
          if (chunk.threadId) {
            setThreadId(chunk.threadId);
          }

          // Error
          if (chunk.error) {
            setError(chunk.error);
          }

          // Done
          if (chunk.done) {
            break;
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError(t("error.generic"));
          console.error(err);
        }
      } finally {
        setLoading(false);
      }
    },
    [threadId, t],
  );

  const handleRetry = useCallback(() => {
    if (lastSubmitData) {
      handleSubmit(lastSubmitData);
    }
  }, [lastSubmitData, handleSubmit]);

  /** HITL: Refine a specific platform's content with user feedback */
  const handleRefine = useCallback(
    (platform: string, feedback: string) => {
      if (!lastSubmitData) return;
      const refineMessage = `Please refine the ${platform} content based on this feedback:\n${feedback}\n\nKeep the same topic and other platforms unchanged. Only improve the ${platform} content.`;
      handleSubmit({
        ...lastSubmitData,
        message: refineMessage,
      });
    },
    [lastSubmitData, handleSubmit],
  );

  /** Handle selecting a conversation from history */
  const handleSelectConversation = useCallback(async (conversationId: string) => {
    try {
      const res = await fetch(`/api/conversations/${conversationId}`);
      if (!res.ok) return;
      const data = await res.json();
      setThreadId(conversationId);
      // Show last assistant message as content
      const lastAssistant = [...(data.messages || [])].reverse().find(
        (m: { role: string }) => m.role === "assistant"
      );
      if (lastAssistant) {
        setContent(lastAssistant.content);
      }
      setReasoning("");
      setToolEvents([]);
      setError(null);
    } catch {
      // Ignore
    }
  }, []);

  /** Format elapsed time as seconds */
  const elapsedText = loading || elapsedMs > 0
    ? `${(elapsedMs / 1000).toFixed(1)}s`
    : "";

  /** Whether there is any generated content to show */
  const hasResult = content.length > 0 || reasoning.length > 0 || toolEvents.length > 0;
  const showEmptyState = !loading && !hasResult && !error;

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-gray-50 via-blue-50/30 to-purple-50/20 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <Header
        title={t("app.title")}
        subtitle={t("app.subtitle")}
        theme={theme}
        locale={locale}
        onToggleTheme={toggleTheme}
        onToggleLocale={toggleLocale}
        onSetLocale={setLocale}
      />

      <div className="flex-1 flex">
        {/* History Sidebar */}
        <HistorySidebar
          currentThreadId={threadId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          language={locale}
        />

        <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-6 space-y-4">
        {/* Empty state — suggested questions */}
        {showEmptyState && (
          <SuggestedQuestions
            t={t}
            onSelect={(q) => setSuggestedTopic(q)}
            disabled={loading}
          />
        )}

        <InputForm
          t={t}
          loading={loading}
          onSubmit={handleSubmit}
          onStop={handleStop}
          externalTopic={suggestedTopic}
          onExternalTopicConsumed={() => setSuggestedTopic("")}
        />

        {/* Error */}
        {error && (
          <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-xl text-sm flex items-center justify-between">
            <span>{error}</span>
            {lastSubmitData && (
              <button
                onClick={handleRetry}
                className="ml-3 px-3 py-1 bg-red-100 dark:bg-red-900/50 hover:bg-red-200 dark:hover:bg-red-800/50 rounded-lg text-xs font-medium transition-colors"
              >
                {t("error.retry")}
              </button>
            )}
          </div>
        )}

        {/* Processing indicators — shown during generation or when results exist */}
        {(loading || hasResult) && (
          <div className="space-y-2">
            {/* Elapsed time & controls bar */}
            {loading && (
              <div className="flex items-center justify-between px-1">
                <span className="text-xs text-gray-400 dark:text-gray-500 tabular-nums">
                  ⏱ {elapsedText}
                </span>
              </div>
            )}
            {!loading && hasResult && (
              <div className="flex items-center justify-between px-1">
                <span className="text-xs text-gray-400 dark:text-gray-500 tabular-nums">
                  ✅ {t("status.complete")} — {elapsedText}
                </span>
                <button
                  onClick={handleNewConversation}
                  className="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 font-medium transition-colors"
                >
                  ✨ {t("action.newConversation")}
                </button>
              </div>
            )}
            {/* Reasoning */}
            {(reasoning || loading) && (
              <ReasoningPanel
                content={reasoning}
                t={t}
                isGenerating={loading}
              />
            )}

            {/* Tool Events */}
            {(toolEvents.length > 0 || loading) && (
              <ToolEvents
                events={toolEvents}
                t={t}
                isGenerating={loading}
              />
            )}
          </div>
        )}

        {/* Content Output */}
        {(content || loading) && (
          <ContentDisplay
            content={content}
            t={t}
            isGenerating={loading}
            onRefine={handleRefine}
          />
        )}
      </main>
      </div>

      <footer className="border-t border-gray-200/50 dark:border-gray-800/50 py-3 text-center text-xs text-gray-400 dark:text-gray-500 bg-white/30 dark:bg-gray-900/30 backdrop-blur-sm">
        <span className="bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent font-medium">TechPulse Social</span>
        <span className="mx-1.5">—</span>
        Agents League @ TechConnect 2026
      </footer>
    </div>
  );
}
