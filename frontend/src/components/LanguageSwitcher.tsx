import { useTranslation } from "react-i18next"
import type { SupportedLanguage } from "../i18n"

export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const currentLanguage = (i18n.language === "ur" ? "ur" : "en") as SupportedLanguage

  function setLanguage(language: SupportedLanguage) {
    if (language !== currentLanguage) {
      i18n.changeLanguage(language)
    }
  }

  return (
    <div className="flex items-center rounded-md border border-white/10 p-0.5 text-xs font-medium">
      <button
        type="button"
        onClick={() => setLanguage("en")}
        aria-pressed={currentLanguage === "en"}
        className={`rounded px-2 py-1 transition-colors ${
          currentLanguage === "en"
            ? "bg-emerald-600 text-white"
            : "text-ink-secondary hover:text-ink-primary"
        }`}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => setLanguage("ur")}
        aria-pressed={currentLanguage === "ur"}
        className={`rounded px-2 py-1 transition-colors ${
          currentLanguage === "ur"
            ? "bg-emerald-600 text-white"
            : "text-ink-secondary hover:text-ink-primary"
        }`}
      >
        اردو
      </button>
    </div>
  )
}
