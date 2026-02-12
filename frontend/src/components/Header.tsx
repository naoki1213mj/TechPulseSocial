import { ChevronDown, Moon, Sparkles, Sun } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Locale } from "../lib/i18n";
import { ALL_LOCALES, LOCALE_META } from "../lib/i18n";

interface HeaderProps {
  title: string;
  subtitle: string;
  theme: "light" | "dark";
  locale: string;
  onToggleTheme: () => void;
  onToggleLocale: () => void;
  onSetLocale?: (locale: Locale) => void;
}

export default function Header({
  title,
  subtitle,
  theme,
  locale,
  onToggleTheme,
  onToggleLocale,
  onSetLocale,
}: HeaderProps) {
  const [langOpen, setLangOpen] = useState(false);
  const langRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (langRef.current && !langRef.current.contains(e.target as Node)) {
        setLangOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const currentMeta = LOCALE_META[locale as Locale] ?? LOCALE_META.en;

  return (
    <header className="header-glass border-b border-white/10 dark:border-gray-800/50 px-6 py-3 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 dark:from-blue-400 dark:via-purple-400 dark:to-pink-400 bg-clip-text text-transparent">
              {title}
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">{subtitle}</p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1.5">
          {/* Language dropdown */}
          <div ref={langRef} className="relative">
            <button
              onClick={() => setLangOpen(!langOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 hover:bg-white/80 dark:hover:bg-gray-700/60 transition-all"
            >
              <span className="text-base leading-none">{currentMeta.flag}</span>
              <span className="text-xs">{currentMeta.nativeLabel}</span>
              <ChevronDown className={`w-3 h-3 transition-transform ${langOpen ? "rotate-180" : ""}`} />
            </button>
            {langOpen && (
              <div className="absolute right-0 mt-1 w-44 rounded-xl border border-gray-200/80 dark:border-gray-700/80 bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl shadow-xl shadow-black/10 dark:shadow-black/30 overflow-hidden animate-dropdown">
                {ALL_LOCALES.map((loc) => {
                  const meta = LOCALE_META[loc];
                  const isActive = loc === locale;
                  return (
                    <button
                      key={loc}
                      onClick={() => {
                        onSetLocale ? onSetLocale(loc) : onToggleLocale();
                        setLangOpen(false);
                      }}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm transition-colors ${
                        isActive
                          ? "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 font-medium"
                          : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                      }`}
                    >
                      <span className="text-base leading-none">{meta.flag}</span>
                      <span>{meta.nativeLabel}</span>
                      <span className="text-xs text-gray-400 ml-auto">{meta.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Theme toggle */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 hover:bg-white/80 dark:hover:bg-gray-700/60 transition-all"
            title="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4 text-amber-500" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-500" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
