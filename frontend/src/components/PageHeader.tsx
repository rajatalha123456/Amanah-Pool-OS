import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { PageHeaderBadges } from "./PageHeaderBadges"
import { translatePhrase } from "../i18n/translate"

interface PageHeaderProps {
  title: string
  subtitle?: string
  screenNumber?: string
  actions?: ReactNode
  showControls?: boolean
}

export function PageHeader({
  title,
  subtitle,
  actions,
  showControls = true,
}: PageHeaderProps) {
  const { i18n } = useTranslation()
  const isUrdu = !!i18n.language && !i18n.language.startsWith("en") // any non-English language

  // Strip any leading screen numbers like "01. ", "Screen 12 - " etc.
  const rawTitle = title
    .replace(/^(?:Screen\s+\d+[\s\:\-]+|\d+[\.\s\-]+)\s*/i, "")
    .trim()

  const displayTitle = isUrdu ? translatePhrase(i18n.language, rawTitle) : rawTitle
  const displaySubtitle = isUrdu && subtitle ? translatePhrase(i18n.language, subtitle) : subtitle

  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight text-ink-primary sm:text-2xl">
            {displayTitle}
          </h1>
        </div>
        {displaySubtitle && <p className="mt-1 text-xs text-ink-secondary sm:text-sm">{displaySubtitle}</p>}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {actions}
        {showControls && <PageHeaderBadges contextName={displayTitle} />}
      </div>
    </div>
  )
}
