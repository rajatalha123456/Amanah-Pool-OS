import type { HTMLAttributes } from "react"
import type { BadgeVariant } from "../types"

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

const variantClasses: Record<BadgeVariant, string> = {
  navy: "bg-navy-700 text-ink-primary",
  emerald: "bg-emerald-600/15 text-emerald-400",
  gold: "bg-gold-500/15 text-gold-400",
  neutral: "bg-white/8 text-ink-secondary",
}

export function Badge({ variant = "neutral", className = "", ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
      {...props}
    />
  )
}
