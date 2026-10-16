import type { HTMLAttributes, ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { translatePhrase } from "../i18n/translate"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string
  actions?: ReactNode
  children: ReactNode
}

export function Card({ title, actions, children, className = "", ...props }: CardProps) {
  const { i18n } = useTranslation()
  const isUrdu = !!i18n.language && !i18n.language.startsWith("en") // any non-English language
  const displayTitle = isUrdu && title ? translatePhrase(i18n.language, title) : title

  return (
    <div
      className={`rounded-xl border border-white/8 bg-navy-900 p-5 ${className}`}
      {...props}
    >
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between gap-4">
          {displayTitle ? (
            <h3 className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">
              {displayTitle}
            </h3>
          ) : (
            <div />
          )}
          {actions && <div>{actions}</div>}
        </div>
      )}
      {children}
    </div>
  )
}
