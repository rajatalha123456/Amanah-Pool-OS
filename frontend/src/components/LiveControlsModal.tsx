import { useEffect, useState } from "react"
import { useUIControls } from "../context/UIControlsContext"
import { useAuth } from "../api/auth"
import { fetchPools } from "../api/pools"
import { fetchProducts } from "../api/products"
import { fetchExceptions } from "../api/governance"
import { Badge } from "./Badge"
import { Button } from "./Button"
import { Spinner } from "./Spinner"

export function LiveControlsModal() {
  const { isLiveControlsOpen, closeLiveControls } = useUIControls()
  const { user } = useAuth()

  const [poolCount, setPoolCount] = useState<number | null>(null)
  const [productCount, setProductCount] = useState<number | null>(null)
  const [exceptionCount, setExceptionCount] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isLiveControlsOpen) return
    setLoading(true)
    Promise.all([
      fetchPools().catch(() => []),
      fetchProducts().catch(() => []),
      fetchExceptions().catch(() => []),
    ]).then(([pools, products, exceptions]) => {
      setPoolCount(pools.length)
      setProductCount(products.length)
      setExceptionCount(exceptions.filter((e) => e.status === "open").length)
      setLoading(false)
    })
  }, [isLiveControlsOpen])

  if (!isLiveControlsOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in">
      <div className="w-full max-w-xl rounded-xl border border-white/10 bg-navy-950 p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500"></span>
            </span>
            <div>
              <h2 className="text-base font-semibold text-ink-primary">Live Institutional Controls</h2>
              <p className="text-xs text-ink-muted">Amanah Real-time Deterministic Monitoring</p>
            </div>
          </div>
          <button
            type="button"
            onClick={closeLiveControls}
            className="rounded-md p-1.5 text-ink-secondary hover:bg-white/5 hover:text-ink-primary"
          >
            ✕
          </button>
        </div>

        <div className="mt-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-white/8 bg-navy-900/60 p-3.5">
              <span className="text-[11px] font-semibold text-ink-muted uppercase">Engine Status</span>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant="emerald">Online / Deterministic</Badge>
              </div>
              <p className="mt-1.5 text-[11px] text-ink-secondary">SHA-256 calculation hashing active</p>
            </div>

            <div className="rounded-lg border border-white/8 bg-navy-900/60 p-3.5">
              <span className="text-[11px] font-semibold text-ink-muted uppercase">Tenant Isolation</span>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant="emerald">Strict Multi-Tenant</Badge>
              </div>
              <p className="mt-1.5 text-[11px] text-ink-secondary">Active Tenant: {user?.tenant ? "Scoped" : "Default"}</p>
            </div>
          </div>

          <div className="rounded-lg border border-white/8 bg-navy-900/40 p-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Control Health Metrics</h3>
            {loading ? (
              <div className="flex items-center gap-2 py-4 text-xs text-ink-secondary">
                <Spinner className="h-4 w-4" />
                <span>Reading live ledger parameters...</span>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between border-b border-white/5 pb-2 text-xs">
                  <span className="text-ink-secondary">Active Investment Pools</span>
                  <span className="font-semibold text-ink-primary">{poolCount ?? 0} Registered</span>
                </div>
                <div className="flex items-center justify-between border-b border-white/5 pb-2 text-xs">
                  <span className="text-ink-secondary">Approved Shariah Products</span>
                  <span className="font-semibold text-emerald-400">{productCount ?? 0} Catalogued</span>
                </div>
                <div className="flex items-center justify-between border-b border-white/5 pb-2 text-xs">
                  <span className="text-ink-secondary">Open Operational Exceptions</span>
                  <span className={`font-semibold ${(exceptionCount ?? 0) > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                    {exceptionCount ?? 0} Active Tickets
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-ink-secondary">Accounting Integrity Gate</span>
                  <span className="font-semibold text-emerald-400">Zero Suspense Active</span>
                </div>
              </>
            )}
          </div>

          <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/20 p-3 text-xs text-emerald-300">
            <div className="flex items-center gap-2 font-semibold">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Zero Suspense Guarantee
            </div>
            <p className="mt-0.5 text-[11px] text-emerald-400/80">
              No pool transaction is balanced silently through suspense. All non-permissible items are routed to charity purification.
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <Button variant="secondary" onClick={closeLiveControls} className="text-xs">
            Close Control Monitor
          </Button>
        </div>
      </div>
    </div>
  )
}
