import { useEffect, useState } from "react"
import { useAuth } from "../api/auth"
import { fetchTenants } from "../api/tenants"
import type { TenantRecord } from "../types"
import { Badge } from "./Badge"

/**
 * Shows the tenant (institution) the signed-in user works in. A user belongs to exactly one tenant and the
 * API refuses any other, so this is an indicator, not a switch; the platform admin manages tenants under
 * Administration.
 */
export function TenantSwitcher() {
  const { user } = useAuth()
  const [tenant, setTenant] = useState<TenantRecord | null>(null)

  // Investors and members may not read the tenant list (deny-by-default); they just see their institution's code.
  const isMember = user?.role === "investor_member"

  useEffect(() => {
    if (!user || isMember) return
    fetchTenants()
      .then((rows) => setTenant(rows.find((t) => t.code === user?.tenant_code) ?? null))
      .catch(() => setTenant(null))
  }, [user, user?.tenant_code, isMember])

  if (isMember && user?.tenant_code) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-white/10 px-3 py-1.5 text-xs">
        <span className="font-mono text-ink-muted">{user.tenant_code}</span>
      </div>
    )
  }
  if (!tenant) return null
  return (
    <div className="flex items-center gap-2 rounded-md border border-white/10 px-3 py-1.5 text-xs">
      <span className="font-semibold text-ink-primary">{tenant.name}</span>
      <span className="font-mono text-ink-muted">{tenant.code}</span>
      <Badge variant={tenant.is_suspended ? "gold" : "emerald"}>{tenant.is_suspended ? "suspended" : "active"}</Badge>
    </div>
  )
}
