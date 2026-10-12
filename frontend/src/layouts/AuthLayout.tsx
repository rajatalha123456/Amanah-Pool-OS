import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { BrandMark } from "../pages/site/SiteIcons"

interface AuthLayoutProps {
  children: ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-navy-950 p-4">
      <div className="site-pattern pointer-events-none absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_at_center,black_15%,transparent_70%)]" />
      <div className="pointer-events-none absolute -left-32 top-0 h-96 w-96 rounded-full bg-emerald-500/10 blur-[100px]" />
      <div className="pointer-events-none absolute -right-24 bottom-0 h-96 w-96 rounded-full bg-gold-500/10 blur-[100px]" />
      <div className="relative w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <BrandMark className="h-12 w-12" />
          <p className="mt-4 text-[11px] font-semibold tracking-widest text-gold-500 uppercase">Novu Labs</p>
          <p className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-ink-primary">Amanah Pool OS</p>
        </div>
        {children}
        <p className="mt-6 text-center text-xs">
          <Link to="/welcome" className="text-ink-secondary transition hover:text-gold-400">
            ← Back to the website
          </Link>
        </p>
      </div>
    </div>
  )
}
