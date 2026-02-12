import { ChevronDown, ChevronUp, Send, Settings2, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface InputFormProps {
  t: (key: string) => string;
  loading: boolean;
  onSubmit: (data: {
    message: string;
    platforms: string[];
    contentType: string;
    language: string;
    reasoningEffort: string;
    reasoningSummary: string;
  }) => void;
  onStop?: () => void;
  /** Allow external topic injection (from SuggestedQuestions) */
  externalTopic?: string;
  onExternalTopicConsumed?: () => void;
}

const PLATFORMS = ["linkedin", "x", "instagram"] as const;
const CONTENT_TYPES = [
  "product_launch",
  "thought_leadership",
  "event_promotion",
  "company_culture",
  "tech_insight",
] as const;

const REASONING_EFFORTS = [
  { value: "low", labelKey: "settings.reasoningEffort.low" },
  { value: "medium", labelKey: "settings.reasoningEffort.medium" },
  { value: "high", labelKey: "settings.reasoningEffort.high" },
] as const;

const REASONING_SUMMARIES = [
  { value: "off", labelKey: "settings.reasoningSummary.off" },
  { value: "auto", labelKey: "settings.reasoningSummary.auto" },
  { value: "concise", labelKey: "settings.reasoningSummary.concise" },
  { value: "detailed", labelKey: "settings.reasoningSummary.detailed" },
] as const;

export default function InputForm({
  t,
  loading,
  onSubmit,
  onStop,
  externalTopic,
  onExternalTopicConsumed,
}: InputFormProps) {
  const [message, setMessage] = useState("");
  const [platforms, setPlatforms] = useState<string[]>(["linkedin", "x"]);
  const [contentType, setContentType] = useState("product_launch");
  const [language, setLanguage] = useState("ja");
  const [reasoningEffort, setReasoningEffort] = useState("medium");
  const [reasoningSummary, setReasoningSummary] = useState("auto");
  const [showSettings, setShowSettings] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Keyboard shortcuts: Ctrl/Cmd+Enter to submit, Escape to stop
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape to stop generation
      if (e.key === "Escape" && loading) {
        e.preventDefault();
        onStop?.();
        return;
      }
      // Ctrl/Cmd + Enter to submit
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (!loading && message.trim() && platforms.length > 0) {
          onSubmit({
            message,
            platforms,
            contentType,
            language,
            reasoningEffort,
            reasoningSummary,
          });
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [loading, message, platforms, contentType, language, reasoningEffort, reasoningSummary, onSubmit, onStop]);

  // Handle external topic injection
  useEffect(() => {
    if (externalTopic) {
      setMessage(externalTopic);
      onExternalTopicConsumed?.();
    }
  }, [externalTopic, onExternalTopicConsumed]);

  const togglePlatform = (p: string) => {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || platforms.length === 0 || loading) return;
    onSubmit({
      message,
      platforms,
      contentType,
      language,
      reasoningEffort,
      reasoningSummary,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="glass-card rounded-2xl p-5 space-y-4 shadow-sm hover:shadow-md transition-shadow"
    >
      {/* Topic input */}
      <div>
        <label className="block text-sm font-medium mb-1.5 text-gray-700 dark:text-gray-300">
          {t("input.topic")}
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          ref={textareaRef}
          placeholder={t("input.topic.placeholder")}
          rows={3}
          className="w-full px-4 py-3 border border-gray-200/60 dark:border-gray-700/60 rounded-xl bg-white/50 dark:bg-gray-800/50 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-400 dark:focus:border-blue-500 outline-none resize-none text-sm transition-all placeholder:text-gray-400"
        />
      </div>

      {/* Platforms */}
      <div>
        <label className="block text-sm font-medium mb-1.5 text-gray-700 dark:text-gray-300">
          {t("input.platforms")}
        </label>
        <div className="flex gap-2">
          {PLATFORMS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => togglePlatform(p)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                platforms.includes(p)
                  ? "platform-chip-active text-white"
                  : "bg-gray-100/80 dark:bg-gray-800/80 text-gray-600 dark:text-gray-400 hover:bg-gray-200/80 dark:hover:bg-gray-700/80 border border-gray-200/50 dark:border-gray-700/50"
              }`}
            >
              {t(`platforms.${p}`)}
            </button>
          ))}
        </div>
      </div>

      {/* Content Type & Language */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1.5 text-gray-700 dark:text-gray-300">
            {t("input.contentType")}
          </label>
          <select
            value={contentType}
            onChange={(e) => setContentType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200/60 dark:border-gray-700/60 rounded-xl bg-white/50 dark:bg-gray-800/50 text-sm outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
          >
            {CONTENT_TYPES.map((ct) => (
              <option key={ct} value={ct}>
                {t(`contentType.${ct}`)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5 text-gray-700 dark:text-gray-300">
            {t("input.language")}
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200/60 dark:border-gray-700/60 rounded-xl bg-white/50 dark:bg-gray-800/50 text-sm outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
          >
            <option value="en">{t("language.en")}</option>
            <option value="ja">{t("language.ja")}</option>
            <option value="ko">{t("language.ko")}</option>
            <option value="zh">{t("language.zh")}</option>
            <option value="es">{t("language.es")}</option>
          </select>
        </div>
      </div>

      {/* AI Settings toggle */}
      <div className="border border-gray-200/50 dark:border-gray-700/50 rounded-xl overflow-hidden bg-white/30 dark:bg-gray-800/30">
        <button
          type="button"
          onClick={() => setShowSettings(!showSettings)}
          className="w-full flex items-center justify-between px-3 py-2.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Settings2 className="w-4 h-4" />
            <span className="font-medium">{t("settings.title")}</span>
            <span className="text-xs text-gray-400 dark:text-gray-500">
              🧠 {reasoningEffort} · {reasoningSummary}
            </span>
          </div>
          {showSettings ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        {showSettings && (
          <div className="px-3 pb-3 pt-1 space-y-3 border-t border-gray-100 dark:border-gray-800">
            {/* Reasoning Effort */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                🧠 {t("settings.reasoningEffort")}
              </label>
              <div className="flex gap-1.5">
                {REASONING_EFFORTS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setReasoningEffort(opt.value)}
                    className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      reasoningEffort === opt.value
                        ? "bg-indigo-600 text-white"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                    }`}
                    title={t(opt.labelKey)}
                  >
                    {opt.value.charAt(0).toUpperCase() + opt.value.slice(1)}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                {t(`settings.reasoningEffort.${reasoningEffort}`)}
              </p>
            </div>

            {/* Reasoning Summary */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                💭 {t("settings.reasoningSummary")}
              </label>
              <div className="flex gap-1.5">
                {REASONING_SUMMARIES.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setReasoningSummary(opt.value)}
                    className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      reasoningSummary === opt.value
                        ? "bg-violet-600 text-white"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                    }`}
                    title={t(opt.labelKey)}
                  >
                    {opt.value.charAt(0).toUpperCase() + opt.value.slice(1)}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                {t(`settings.reasoningSummary.${reasoningSummary}`)}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Submit / Stop */}
      <div className="flex gap-2">
        {loading ? (
          <button
            type="button"
            onClick={onStop}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl text-sm font-semibold transition-all shadow-sm hover:shadow-md"
          >
            <Square className="w-4 h-4" />
            {t("input.stop")}
          </button>
        ) : (
          <button
            type="submit"
            disabled={!message.trim() || platforms.length === 0}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 btn-gradient disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-sm font-semibold"
          >
            <Send className="w-4 h-4" />
            {t("input.submit")}
            <span className="text-xs opacity-60 ml-1">⌘↵</span>
          </button>
        )}
      </div>
    </form>
  );
}
