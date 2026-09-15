import type { ReactNode } from "react"

interface AuthLayoutProps {
  children: ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-950 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <p className="text-[11px] font-semibold tracking-widest text-gold-500 uppercase">
            Novu Labs
          </p>
          <p className="mt-1 text-xl font-semibold text-ink-primary">Amanah Pool OS</p>
        </div>
        {children}
      </div>
    </div>
  )
}
