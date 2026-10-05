import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { PageHeaderBadges } from "./PageHeaderBadges"
import { translateToUrdu } from "../i18n/urduDictionary"

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
  const isUrdu = i18n.language?.startsWith("ur")

  // Strip any leading screen numbers like "01. ", "Screen 12 - " etc.
  const rawTitle = title
    .replace(/^(?:Screen\s+\d+[\s\:\-]+|\d+[\.\s\-]+)\s*/i, "")
    .trim()

  const displayTitle = isUrdu ? translateToUrdu(rawTitle) : rawTitle
  const displaySubtitle = isUrdu && subtitle ? translateToUrdu(subtitle) : subtitle

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
