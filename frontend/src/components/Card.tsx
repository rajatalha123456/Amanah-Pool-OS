import type { HTMLAttributes, ReactNode } from "react"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string
  children: ReactNode
}

export function Card({ title, children, className = "", ...props }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-white/8 bg-navy-900 p-5 ${className}`}
      {...props}
    >
      {title && (
        <h3 className="mb-3 text-xs font-semibold tracking-wide text-ink-secondary uppercase">
          {title}
        </h3>
      )}
      {children}
    </div>
  )
}
