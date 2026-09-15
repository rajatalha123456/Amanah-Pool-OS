import type { HTMLAttributes, ReactNode } from "react"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string
  children: ReactNode
}

export function Card({ title, children, className = "", ...props }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-navy-700 bg-navy-900 p-5 shadow-sm ${className}`}
      {...props}
    >
      {title && (
        <h3 className="mb-3 text-sm font-semibold tracking-wide text-gray-200 uppercase">
          {title}
        </h3>
      )}
      {children}
    </div>
  )
}
