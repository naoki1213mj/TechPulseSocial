import { ChevronLeft, ChevronRight, MessageSquare, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface ConversationSummary {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

interface HistorySidebarProps {
  currentThreadId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  language: "en" | "ja";
}

const labels = {
  en: {
    history: "History",
    newChat: "New Chat",
    noHistory: "No conversations yet",
    deleteConfirm: "Delete this conversation?",
  },
  ja: {
    history: "履歴",
    newChat: "新規チャット",
    noHistory: "会話履歴がありません",
    deleteConfirm: "この会話を削除しますか？",
  },
};

export default function HistorySidebar({
  currentThreadId,
  onSelectConversation,
  onNewConversation,
  language,
}: HistorySidebarProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const t = labels[language];

  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch("/api/conversations");
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch {
      // Silently fail — history is optional
    }
  }, []);

  useEffect(() => {
    fetchConversations();
    // Poll every 30s
    const interval = setInterval(fetchConversations, 30000);
    return () => clearInterval(interval);
  }, [fetchConversations]);

  // Refresh after a new message
  useEffect(() => {
    if (currentThreadId) {
      const timer = setTimeout(fetchConversations, 2000);
      return () => clearTimeout(timer);
    }
  }, [currentThreadId, fetchConversations]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm(t.deleteConfirm)) return;
    try {
      await fetch(`/api/conversations/${id}`, { method: "DELETE" });
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch {
      // Ignore
    }
  };

  const formatTime = (iso: string) => {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return language === "ja" ? "たった今" : "just now";
    if (diffMin < 60)
      return language === "ja" ? `${diffMin}分前` : `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24)
      return language === "ja" ? `${diffHr}時間前` : `${diffHr}h ago`;
    return d.toLocaleDateString(language === "ja" ? "ja-JP" : "en-US", {
      month: "short",
      day: "numeric",
    });
  };

  if (collapsed) {
    return (
      <div className="flex flex-col items-center py-4 px-1 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500"
          title={t.history}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={onNewConversation}
          className="mt-2 p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-blue-500"
          title={t.newChat}
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 flex flex-col border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          {t.history}
        </h2>
        <button
          onClick={() => setCollapsed(true)}
          className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-3 py-2">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-dashed border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t.newChat}
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 ? (
          <p className="text-xs text-gray-400 text-center mt-4">{t.noHistory}</p>
        ) : (
          <ul className="space-y-1">
            {conversations.map((convo) => (
              <li key={convo.id}>
                <button
                  onClick={() => onSelectConversation(convo.id)}
                  className={`w-full text-left group flex items-start gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                    convo.id === currentThreadId
                      ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                      : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="truncate font-medium text-xs">
                      {convo.title || "Untitled"}
                    </p>
                    <p className="text-[10px] text-gray-400 mt-0.5">
                      {formatTime(convo.updatedAt)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, convo.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-400 transition-opacity"
                    title="Delete"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
