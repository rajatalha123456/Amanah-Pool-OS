import { translateToArabic } from "./arabicDictionary"
import { translateToUrdu } from "./urduDictionary"

/** A shared-component phrase in the current language; English (or an unknown phrase) is returned unchanged. */
export function translatePhrase(language: string | undefined, text: string): string {
  if (language?.startsWith("ur")) return translateToUrdu(text)
  if (language?.startsWith("ar")) return translateToArabic(text)
  return text
}
