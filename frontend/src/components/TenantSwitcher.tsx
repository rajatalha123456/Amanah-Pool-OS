import { useEffect, useRef, useState } from "react"
import { useAuth } from "../api/auth"

// TODO(multi-tenant): the backend currently supports only one tenant
// per user (see apps.accounts.User.tenant on the backend). Once a user
// can belong to / access multiple tenants, this dropdown should:
//   1. Fetch the real list of tenants available to the current user
//      from an API (instead of the single `user.tenant_code` value).
//   2. On selecting a different tenant, set the new tenant code as
//      "amanah_tenant_code" in localStorage (see src/api/axios.ts,
//      TENANT_CODE_KEY) so it is sent as X-Tenant-Code on all
//      subsequent requests.
//   3. Trigger a reload/refetch of tenant-scoped data (e.g. a full
//      page reload, or invalidating any cached queries) since nearly
//      everything in the app is tenant-scoped.

export function TenantSwitcher() {
  const { user } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  const tenantName = user?.tenant_code ?? "No tenant"

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-ink-secondary transition-colors hover:bg-white/10 hover:text-ink-primary"
      >
        <span>{tenantName}</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          className={`h-3.5 w-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-2 w-56 rounded-md border border-white/8 bg-navy-900 py-1 shadow-lg">
          <p className="px-3 py-1.5 text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
            Tenant
          </p>
          <div className="flex items-center justify-between px-3 py-2 text-sm text-ink-primary">
            <span>{tenantName}</span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              className="h-4 w-4 text-emerald-400"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>
        </div>
      )}
    </div>
  )
}
