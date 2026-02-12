import { Sparkles } from "lucide-react";

interface SuggestedQuestionsProps {
  t: (key: string) => string;
  onSelect: (question: string) => void;
  disabled?: boolean;
}

const SUGGESTIONS = [
  { key: "suggestions.1", icon: "🚀" },
  { key: "suggestions.2", icon: "🎤" },
  { key: "suggestions.3", icon: "👥" },
  { key: "suggestions.4", icon: "📊" },
] as const;

export default function SuggestedQuestions({
  t,
  onSelect,
  disabled = false,
}: SuggestedQuestionsProps) {
  return (
    <div className="mt-6 mb-2">
      <div className="flex items-center gap-2 mb-4 text-sm text-gray-500 dark:text-gray-400">
        <Sparkles className="w-4 h-4 text-purple-500" />
        <span className="font-medium">{t("suggestions.title")}</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {SUGGESTIONS.map((item) => (
          <button
            key={item.key}
            onClick={() => onSelect(t(item.key))}
            disabled={disabled}
            className="float-in gradient-border flex items-center gap-3 px-4 py-3.5 text-left text-sm rounded-xl glass-card hover:bg-blue-50/50 dark:hover:bg-blue-950/20 hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <span className="text-xl shrink-0 group-hover:scale-110 transition-transform">{item.icon}</span>
            <span className="text-gray-700 dark:text-gray-300 line-clamp-2 font-medium">
              {t(item.key)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
