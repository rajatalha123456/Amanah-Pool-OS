import { useEffect, useState, useMemo, type FormEvent } from "react"
import { Card } from "../../components/Card"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { StatCard } from "../../components/StatCard"
import { Table, type TableColumn } from "../../components/Table"
import { PageHeader } from "../../components/PageHeader"
import { Modal } from "../../components/Modal"
import { useAuth } from "../../api/auth"
import {
  fetchTenants,
  createTenant,
  suspendTenant,
  reactivateTenant,
  createLegalEntity,
} from "../../api/tenants"
import { extractErrorMessage } from "../../api/errors"
import { TENANT_CODE_KEY } from "../../api/axios"
import type { TenantRecord, LegalEntityRecord } from "../../types"

interface TenantManagementProps {
  hideHeader?: boolean
}

export function TenantManagement({ hideHeader }: TenantManagementProps) {
  const { user, loadCurrentUser } = useAuth()
  const isSuperAdmin = user?.role === "platform_super_admin"

  const [tenants, setTenants] = useState<TenantRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [actionLoading, setActionLoading] = useState(false)

  // Active tenant in localStorage
  const activeTenantCode = localStorage.getItem(TENANT_CODE_KEY) || user?.tenant_code || "NOVU-DEMO"

  // Modal: New Tenant
  const [showNewTenantModal, setShowNewTenantModal] = useState(false)
  const [newCode, setNewCode] = useState("")
  const [newName, setNewName] = useState("")
  const [newResidency, setNewResidency] = useState("PK")
  const [newDomain, setNewDomain] = useState("")

  // Modal: Legal Entities Drawer
  const [selectedTenantForEntities, setSelectedTenantForEntities] = useState<TenantRecord | null>(null)
  const [showNewEntityModal, setShowNewEntityModal] = useState(false)
  const [entityName, setEntityName] = useState("")
  const [entityRegNum, setEntityRegNum] = useState("")
  const [entityJurisdiction, setEntityJurisdiction] = useState("Pakistan")
  const [entityCurrency, setEntityCurrency] = useState("PKR")
  const [entityTimezone, setEntityTimezone] = useState("Asia/Karachi")

  const loadAllTenants = async () => {
    setLoading(true)
    setError("")
    try {
      const data = await fetchTenants()
      setTenants(data)
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load tenants."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAllTenants()
  }, [])

  const { totalLegalEntities, totalUsersAcrossTenants } = useMemo(() => {
    let entities = 0
    let usersCount = 0
    for (const t of tenants) {
      entities += t.legal_entities?.length || 0
      usersCount += t.user_count || 0
    }
    return {
      totalLegalEntities: entities,
      totalUsersAcrossTenants: usersCount,
    }
  }, [tenants])

  async function handleSwitchTenant(targetCode: string) {
    localStorage.setItem(TENANT_CODE_KEY, targetCode)
    await loadCurrentUser()
    window.location.reload()
  }

  async function handleCreateTenant(e: FormEvent) {
    e.preventDefault()
    setActionLoading(true)
    setError("")
    try {
      const created = await createTenant({
        code: newCode.trim().toUpperCase(),
        name: newName.trim(),
        data_residency: newResidency,
        domain: newDomain.trim() || undefined,
      })
      setTenants((prev) => [...prev, created])
      setShowNewTenantModal(false)
      setNewCode("")
      setNewName("")
      setNewDomain("")
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to create tenant."))
    } finally {
      setActionLoading(false)
    }
  }

  async function handleToggleSuspend(target: TenantRecord) {
    setActionLoading(true)
    setError("")
    try {
      const updated = target.is_suspended
        ? await reactivateTenant(target.id)
        : await suspendTenant(target.id)
      setTenants((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to update tenant status."))
    } finally {
      setActionLoading(false)
    }
  }

  async function handleCreateLegalEntity(e: FormEvent) {
    e.preventDefault()
    if (!selectedTenantForEntities) return
    setActionLoading(true)
    setError("")
    try {
      const created = await createLegalEntity({
        tenant: selectedTenantForEntities.id,
        name: entityName.trim(),
        registration_number: entityRegNum.trim() || undefined,
        jurisdiction: entityJurisdiction.trim(),
        base_currency: entityCurrency.trim(),
        timezone: entityTimezone.trim(),
      })
      setSelectedTenantForEntities((prev) => {
        if (!prev) return null
        return {
          ...prev,
          legal_entities: [...prev.legal_entities, created],
        }
      })
      setTenants((prev) =>
        prev.map((t) =>
          t.id === selectedTenantForEntities.id
            ? { ...t, legal_entities: [...t.legal_entities, created] }
            : t,
        ),
      )
      setShowNewEntityModal(false)
      setEntityName("")
      setEntityRegNum("")
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to create legal entity."))
    } finally {
      setActionLoading(false)
    }
  }

  const columns: TableColumn<TenantRecord>[] = [
    {
      header: "Tenant Code",
      accessor: (t) => (
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-xs text-ink-primary">{t.code}</span>
          {t.code === activeTenantCode && (
            <Badge variant="emerald">ACTIVE CONTEXT</Badge>
          )}
        </div>
      ),
    },
    {
      header: "Institution Name",
      accessor: (t) => (
        <div>
          <span className="text-xs font-semibold text-ink-primary block">{t.name}</span>
          <span className="text-[10px] text-ink-muted">{t.domain || "Internal Enterprise Domain"}</span>
        </div>
      ),
    },
    {
      header: "Residency",
      accessor: (t) => (
        <span className="rounded bg-navy-800 px-2 py-0.5 font-mono text-xs text-emerald-400">
          {t.data_residency} (Local Cloud)
        </span>
      ),
    },
    {
      header: "Users",
      accessor: (t) => <span className="text-xs text-ink-primary font-semibold">{t.user_count}</span>,
    },
    {
      header: "Entities",
      accessor: (t) => (
        <button
          type="button"
          onClick={() => setSelectedTenantForEntities(t)}
          className="text-xs text-emerald-400 underline hover:text-emerald-300"
        >
          {t.legal_entities?.length || 0} Entities
        </button>
      ),
    },
    {
      header: "Status",
      accessor: (t) => (
        <Badge variant={t.is_suspended ? "navy" : "emerald"}>
          {t.is_suspended ? "SUSPENDED" : "ACTIVE"}
        </Badge>
      ),
    },
    {
      header: "Actions",
      accessor: (t) => (
        <div className="flex items-center gap-2">
          {t.code !== activeTenantCode && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => handleSwitchTenant(t.code)}
            >
              Switch To
            </Button>
          )}
          {isSuperAdmin && (
            <Button
              size="sm"
              variant={t.is_suspended ? "primary" : "secondary"}
              onClick={() => handleToggleSuspend(t)}
              disabled={actionLoading}
            >
              {t.is_suspended ? "Reactivate" : "Suspend"}
            </Button>
          )}
        </div>
      ),
    },
  ]

  const entityColumns: TableColumn<LegalEntityRecord>[] = [
    { header: "Entity Name", accessor: (e) => e.name },
    { header: "Registration #", accessor: (e) => e.registration_number || "—" },
    { header: "Jurisdiction", accessor: (e) => e.jurisdiction },
    { header: "Currency", accessor: (e) => e.base_currency },
    { header: "Timezone", accessor: (e) => e.timezone },
  ]

  return (
    <div className="space-y-6">
      {!hideHeader && (
        <PageHeader
          screenNumber="40"
          title="40. Multi-Tenant Switching & Configuration"
          subtitle="Strict Row-Level ContextVar Isolation, Legal Entity Scopes, and Residency Controls"
          actions={
            isSuperAdmin ? (
              <Button variant="primary" onClick={() => setShowNewTenantModal(true)}>
                + Provision New Tenant
              </Button>
            ) : undefined
          }
        />
      )}

      {error && (
        <div className="rounded border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Screen 40 StatCards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          label="Active Tenants"
          value={tenants.length.toString()}
          subtext={`${totalUsersAcrossTenants} Users Provisioned Across Tenants`}
        />
        <StatCard
          label="Legal Entities"
          value={totalLegalEntities.toString()}
          subtext="Corporate Banking Structures"
        />
        <StatCard
          label="Data Residency"
          value="PK-Karachi"
          subtext="Local Sovereignty Enforced"
        />
        <StatCard
          label="Isolation Barrier"
          value="STRICT CONTEXT"
          subtext="TenantScopedModel Active"
        />
      </div>

      {/* Active Tenant Context Card */}
      <Card title="Active Session Scope & Tenant Switcher">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-xs text-ink-secondary">
              All backend queries are strictly scoped using thread-local contextvars matching the active tenant header:
            </p>
            <div className="mt-2 flex items-center gap-3">
              <span className="font-mono text-sm font-bold text-ink-primary">
                Current Tenant: {activeTenantCode}
              </span>
              <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
                X-Tenant-Code Attached
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-muted">Quick Switch:</span>
            <select
              value={activeTenantCode}
              onChange={(e) => handleSwitchTenant(e.target.value)}
              className="rounded border border-white/10 bg-navy-800 px-3 py-1.5 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none"
            >
              {tenants.map((t) => (
                <option key={t.id} value={t.code}>
                  {t.name} ({t.code})
                </option>
              ))}
            </select>
            {hideHeader && isSuperAdmin && (
              <Button variant="primary" onClick={() => setShowNewTenantModal(true)}>
                + Provision Tenant
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Tenants Table */}
      <Card title="Tenant Organizations & Sovereign Datastores">
        {loading ? (
          <div className="flex items-center gap-2 py-12 text-ink-secondary">
            <Spinner className="h-5 w-5" />
            <span className="text-sm">Loading tenants directory...</span>
          </div>
        ) : tenants.length === 0 ? (
          <p className="py-8 text-center text-xs text-ink-muted">No tenants provisioned.</p>
        ) : (
          <Table
            columns={columns}
            data={tenants}
            keyField={(t) => t.id}
          />
        )}
      </Card>

      {/* Modal: New Tenant */}
      {showNewTenantModal && (
        <Modal
          title="Provision New Tenant Organization"
          onClose={() => setShowNewTenantModal(false)}
        >
          <form onSubmit={handleCreateTenant} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                Tenant Code (Unique ID) *
              </label>
              <input
                type="text"
                placeholder="e.g. MEEZAN-ISL"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value)}
                required
                className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary uppercase font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                Institution Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Meezan Islamic Bank Ltd"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
                className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                  Data Residency *
                </label>
                <select
                  value={newResidency}
                  onChange={(e) => setNewResidency(e.target.value)}
                  className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                >
                  <option value="PK">PK (Pakistan Sovereign Cloud)</option>
                  <option value="AE">AE (UAE DIFC / ADGM)</option>
                  <option value="MY">MY (Malaysia BNM)</option>
                  <option value="SA">SA (Saudi Arabia SAMA)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                  Custom Domain
                </label>
                <input
                  type="text"
                  placeholder="e.g. islamic.meezanbank.com"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button variant="secondary" onClick={() => setShowNewTenantModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" disabled={actionLoading}>
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Provision Tenant"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Legal Entities Drawer */}
      {selectedTenantForEntities && (
        <Modal
          title={`Legal Entities for ${selectedTenantForEntities.name}`}
          onClose={() => setSelectedTenantForEntities(null)}
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs text-ink-secondary">
                Registered corporate entities and banking licenses under {selectedTenantForEntities.code}:
              </p>
              {isSuperAdmin && (
                <Button size="sm" variant="secondary" onClick={() => setShowNewEntityModal(true)}>
                  + Add Entity
                </Button>
              )}
            </div>

            {selectedTenantForEntities.legal_entities?.length === 0 ? (
              <p className="py-6 text-center text-xs text-ink-muted">
                No legal entities configured for this tenant.
              </p>
            ) : (
              <Table
                columns={entityColumns}
                data={selectedTenantForEntities.legal_entities}
                keyField={(e) => e.id}
              />
            )}

            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => setSelectedTenantForEntities(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Add Legal Entity */}
      {showNewEntityModal && selectedTenantForEntities && (
        <Modal
          title={`Add Legal Entity to ${selectedTenantForEntities.name}`}
          onClose={() => setShowNewEntityModal(false)}
        >
          <form onSubmit={handleCreateLegalEntity} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                Entity Legal Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Novu Capital Ltd"
                value={entityName}
                onChange={(e) => setEntityName(e.target.value)}
                required
                className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                Registration / License Number
              </label>
              <input
                type="text"
                placeholder="e.g. SEC-PK-981240"
                value={entityRegNum}
                onChange={(e) => setEntityRegNum(e.target.value)}
                className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                  Jurisdiction
                </label>
                <input
                  type="text"
                  value={entityJurisdiction}
                  onChange={(e) => setEntityJurisdiction(e.target.value)}
                  className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                  Base Currency
                </label>
                <input
                  type="text"
                  value={entityCurrency}
                  onChange={(e) => setEntityCurrency(e.target.value)}
                  className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted mb-1">
                  Timezone
                </label>
                <input
                  type="text"
                  value={entityTimezone}
                  onChange={(e) => setEntityTimezone(e.target.value)}
                  className="w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button variant="secondary" onClick={() => setShowNewEntityModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" disabled={actionLoading}>
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Save Entity"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Bottom Control Total Bar matching Catalogue Screen 40 */}
      <div className="mt-6 border-t border-white/8 pt-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">
              TENANT ISOLATION BARRIER
            </p>
            <p className="text-base font-bold text-ink-primary">
              100% Strict <span className="text-emerald-400 text-xs">Row-Level</span>
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">ENTITIES REGISTERED</p>
            <p className="text-base font-bold text-emerald-400">{totalLegalEntities} Corporate Scopes</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">DATA RESIDENCY</p>
            <p className="text-base font-bold text-emerald-400">Verified Sovereign</p>
          </div>
        </div>
      </div>
    </div>
  )
}
