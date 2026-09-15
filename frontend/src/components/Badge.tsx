import type { HTMLAttributes } from "react"
import type { BadgeVariant } from "../types"

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

const variantClasses: Record<BadgeVariant, string> = {
  navy: "bg-navy-700 text-gray-100",
  emerald: "bg-emerald-100 text-emerald-700",
  gold: "bg-gold-100 text-gold-700",
  neutral: "bg-gray-700 text-gray-100",
}

export function Badge({ variant = "neutral", className = "", ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
      {...props}
    />
  )
}
