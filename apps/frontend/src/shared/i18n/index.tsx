import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { messages, type MessageKey } from "./messages";
export type Locale = "fr" | "en" | "es";
export type Translate = (
  key: MessageKey,
  parameters?: Record<string, string | number>,
) => string;
const isLocale = (value: unknown): value is Locale =>
  value === "fr" || value === "en" || value === "es";
function translator(locale: Locale): Translate {
  return (key, parameters = {}) => {
    const message =
      locale === "fr" ? key : messages[key][locale === "en" ? 0 : 1];
    return message.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
      String(parameters[name] ?? placeholder),
    );
  };
}
function initialPreference(): Locale {
  try {
    const saved = localStorage.getItem("atlasTCG.locale");
    return isLocale(saved) ? saved : "fr";
  } catch {
    // Storage may be unavailable in a private or restricted browser session.
    return "fr";
  }
}
function languageLabel(locale: Locale, code: string) {
  const parsed = new Intl.Locale(code);
  const language =
    new Intl.DisplayNames([locale], { type: "language" }).of(parsed.language) ??
    code;
  const region = parsed.region
    ? new Intl.DisplayNames([locale], { type: "region" }).of(parsed.region)
    : undefined;
  const name = region ? `${language} (${region})` : language;
  return name.charAt(0).toLocaleUpperCase(locale) + name.slice(1);
}
const I18nContext = createContext({
  locale: "fr" as Locale,
  setLocale: (_value: string) => {},
  t: translator("fr"),
  languageName: (code: string) => languageLabel("fr", code),
});
export function I18nProvider({
  children,
  initialLocale,
}: {
  children: ReactNode;
  initialLocale?: Locale;
}) {
  const [locale, setPreference] = useState<Locale>(
    () => initialLocale ?? initialPreference(),
  );
  useEffect(() => {
    document.documentElement.lang = locale;
    try {
      localStorage.setItem("atlasTCG.locale", locale);
    } catch {
      /* The in-memory preference still works when storage is unavailable. */
    }
  }, [locale]);
  return (
    <I18nContext.Provider
      value={{
        locale,
        t: translator(locale),
        setLocale: (value) => {
          if (isLocale(value)) setPreference(value);
        },
        languageName: (code) => languageLabel(locale, code),
      }}
    >
      {children}
    </I18nContext.Provider>
  );
}
export const useI18n = () => useContext(I18nContext);
