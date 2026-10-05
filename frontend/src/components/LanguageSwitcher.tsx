import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { applyDocumentDirection, LANGUAGE_STORAGE_KEY, type SupportedLanguage } from "../i18n"

export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const [currentLanguage, setCurrentLanguage] = useState<SupportedLanguage>(() => {
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    if (stored === "ur") return "ur"
    if (i18n.language?.startsWith("ur")) return "ur"
    return "en"
  })

  useEffect(() => {
    function onLangChange(lng: string) {
      const next = (lng?.startsWith("ur") ? "ur" : "en") as SupportedLanguage
      setCurrentLanguage(next)
      applyDocumentDirection(next)
    }

    i18n.on("languageChanged", onLangChange)
    return () => {
      i18n.off("languageChanged", onLangChange)
    }
  }, [i18n])

  function setLanguage(language: SupportedLanguage) {
    setCurrentLanguage(language)
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
    } catch {
      // ignore
    }
    applyDocumentDirection(language)
    i18n.changeLanguage(language)
  }

  return (
    <div className="flex items-center rounded-md border border-white/10 p-0.5 text-xs font-medium">
      <button
        type="button"
        onClick={() => setLanguage("en")}
        aria-pressed={currentLanguage === "en"}
        className={`rounded px-2.5 py-1 font-semibold transition-all ${
          currentLanguage === "en"
            ? "bg-emerald-600 text-white shadow-sm"
            : "text-ink-secondary hover:text-ink-primary hover:bg-white/5"
        }`}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => setLanguage("ur")}
        aria-pressed={currentLanguage === "ur"}
        className={`rounded px-2.5 py-1 font-semibold transition-all ${
          currentLanguage === "ur"
            ? "bg-emerald-600 text-white shadow-sm"
            : "text-ink-secondary hover:text-ink-primary hover:bg-white/5"
        }`}
      >
        اردو
      </button>
    </div>
  )
}
