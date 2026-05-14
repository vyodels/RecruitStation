import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type UiLanguage = "en" | "zh-CN";

interface I18nContextValue {
  language: UiLanguage;
  setLanguage(language: UiLanguage): void;
  copy(en: string, zh: string): string;
}

const STORAGE_KEY = "recruit-station:ui-language";

const I18nContext = createContext<I18nContextValue | null>(null);

function detectInitialLanguage(): UiLanguage {
  if (typeof window === "undefined") {
    return "en";
  }
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "en" || stored === "zh-CN") {
    return stored;
  }
  const browserLanguage = String(window.navigator.language || "").toLowerCase();
  return browserLanguage.startsWith("zh") ? "zh-CN" : "en";
}

export function I18nProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [language, setLanguage] = useState<UiLanguage>(detectInitialLanguage);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      copy: (en, zh) => (language === "zh-CN" ? zh : en),
    }),
    [language],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const value = useContext(I18nContext);
  if (!value) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return value;
}
