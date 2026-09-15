import type { ReactNode } from "react"
import { PageHeaderBadges } from "./PageHeaderBadges"

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-ink-primary">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-secondary">{subtitle}</p>}
      </div>
      {actions ?? <PageHeaderBadges />}
    </div>
  )
}
