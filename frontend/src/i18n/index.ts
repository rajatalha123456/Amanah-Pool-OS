import i18n from "i18next"
import { initReactI18next } from "react-i18next"
import en from "./en.json"
import ur from "./ur.json"

export const LANGUAGE_STORAGE_KEY = "language"
export type SupportedLanguage = "en" | "ur"

function getStoredLanguage(): SupportedLanguage {
  try {
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    return stored === "ur" ? "ur" : "en"
  } catch {
    return "en"
  }
}

export function applyDocumentDirection(language: SupportedLanguage) {
  document.documentElement.dir = language === "ur" ? "rtl" : "ltr"
  document.documentElement.lang = language
}

const initialLanguage = getStoredLanguage()

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ur: { translation: ur },
  },
  lng: initialLanguage,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
})

applyDocumentDirection(initialLanguage)

i18n.on("languageChanged", (language) => {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  } catch {
    // ignore storage failures (e.g. private browsing)
  }
  applyDocumentDirection(language === "ur" ? "ur" : "en")
})

export default i18n
