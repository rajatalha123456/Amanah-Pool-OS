import type { ButtonHTMLAttributes } from "react"

type ButtonVariant = "primary" | "secondary" | "outline"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-emerald-600 text-white hover:bg-emerald-500 focus-visible:outline-emerald-500",
  secondary:
    "bg-navy-700 text-white hover:bg-navy-600 focus-visible:outline-navy-500",
  outline:
    "bg-transparent text-emerald-500 border border-emerald-600 hover:bg-emerald-600/10 focus-visible:outline-emerald-500",
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`}
      {...props}
    />
  )
}
