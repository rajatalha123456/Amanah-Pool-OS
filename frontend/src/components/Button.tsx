import type { ButtonHTMLAttributes } from "react"
import { useTranslation } from "react-i18next"
import { translateToUrdu } from "../i18n/urduDictionary"

type ButtonVariant = "primary" | "secondary" | "outline" | "gold"
type ButtonSize = "sm" | "md" | "lg"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-emerald-600 text-white hover:bg-emerald-500 focus-visible:outline-emerald-500",
  secondary:
    "bg-navy-700 text-ink-primary hover:bg-navy-600 focus-visible:outline-navy-500",
  outline:
    "bg-transparent text-emerald-400 border border-emerald-600 hover:bg-emerald-600/10 focus-visible:outline-emerald-500",
  gold: "bg-gold-500 text-navy-950 hover:bg-gold-400 focus-visible:outline-gold-500",
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-5 py-2.5 text-base",
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  disabled,
  "aria-busy": ariaBusy,
  children,
  ...props
}: ButtonProps) {
  const { i18n } = useTranslation()
  const isUrdu = i18n.language?.startsWith("ur")
  const content = isUrdu && typeof children === "string" ? translateToUrdu(children) : children

  return (
    <button
      disabled={disabled}
      aria-disabled={disabled || undefined}
      aria-busy={ariaBusy}
      className={`inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {content}
    </button>
  )
}
