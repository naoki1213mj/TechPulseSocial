import { useCallback, useState } from "react";
import type { Locale } from "../lib/i18n";
import { ALL_LOCALES, t } from "../lib/i18n";

export function useI18n(initial: Locale = "ja") {
  const [locale, setLocale] = useState<Locale>(initial);

  const translate = useCallback(
    (key: string) => t(key, locale),
    [locale],
  );

  const toggleLocale = useCallback(() => {
    setLocale((prev) => {
      const idx = ALL_LOCALES.indexOf(prev);
      return ALL_LOCALES[(idx + 1) % ALL_LOCALES.length];
    });
  }, []);

  return { locale, setLocale, t: translate, toggleLocale } as const;
}
