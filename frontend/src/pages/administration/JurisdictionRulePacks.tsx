import { useEffect, useState, type FormEvent } from "react"
import { Card } from "../../components/Card"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { PageHeader } from "../../components/PageHeader"
import { Spinner } from "../../components/Spinner"
import { StatCard } from "../../components/StatCard"
import { Modal } from "../../components/Modal"
import { Table, type TableColumn } from "../../components/Table"
import { useAuth } from "../../api/auth"
import { fetchPools } from "../../api/pools"
import {
  fetchJurisdictionRulePacks,
  createJurisdictionRulePack,
  activateJurisdictionRulePack,
} from "../../api/jurisdiction"
import {
  fetchReservePolicies,
  createReservePolicy,
} from "../../api/reservePolicies"
import { extractErrorMessage } from "../../api/errors"
import type { JurisdictionRulePack, Pool, ReservePolicy } from "../../types"

interface JurisdictionRulePacksProps {
  hideHeader?: boolean
}

export function JurisdictionRulePacks({ hideHeader }: JurisdictionRulePacksProps = {}) {
  const { user } = useAuth()
  const canManage =
    user?.role === "platform_super_admin" ||
    user?.role === "compliance_officer" ||
    user?.role === "risk_manager"

  const [rulePacks, setRulePacks] = useState<JurisdictionRulePack[]>([])
  const [reservePolicies, setReservePolicies] = useState<ReservePolicy[]>([])
  const [pools, setPools] = useState<Pool[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  // New Rule Pack Modal
  const [showNewPackModal, setShowNewPackModal] = useState(false)
  const [packCode, setPackCode] = useState("")
  const [packName, setPackName] = useState("")
  const [packVersion, setPackVersion] = useState("2026.01")
  const [packEffectiveDate, setPackEffectiveDate] = useState("2026-01-01")
  const [packDescription, setPackDescription] = useState("")
  const [packConfigJson, setPackConfigJson] = useState(
    JSON.stringify(
      {
        per_ceiling_pct: 2.0,
        irr_ceiling_pct: 5.0,
        notice_period_days: 30,
        mudarib_share_cap_pct: 20.0,
        purification_interval: "monthly",
      },
      null,
      2,
    ),
  )

  // New Reserve Policy Modal
  const [showPolicyModal, setShowPolicyModal] = useState(false)
  const [policyPool, setPolicyPool] = useState("")
  const [reserveType, setReserveType] = useState<"per" | "irr">("per")
  const [regulatoryCeiling, setRegulatoryCeiling] = useState("2.00")
  const [boardTarget, setBoardTarget] = useState("1.50")
  const [policyEffectiveFrom, setPolicyEffectiveFrom] = useState("2026-01-01")

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [packs, policies, poolsData] = await Promise.all([
        fetchJurisdictionRulePacks(),
        fetchReservePolicies(),
        fetchPools(),
      ])
      setRulePacks(packs)
      setReservePolicies(policies)
      setPools(poolsData)
      if (poolsData.length > 0 && !policyPool) {
        setPolicyPool(poolsData[0].id)
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleActivatePack = async (packId: string, setAsDefault: boolean) => {
    setActionLoading(true)
    try {
      await activateJurisdictionRulePack(packId, setAsDefault)
      await loadData()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const handleCreatePack = async (e: FormEvent) => {
    e.preventDefault()
    setActionLoading(true)
    try {
      let config = {}
      try {
        config = JSON.parse(packConfigJson)
      } catch {
        setError("Invalid JSON in rules config")
        setActionLoading(false)
        return
      }

      await createJurisdictionRulePack({
        code: packCode,
        name: packName,
        version: packVersion,
        effective_date: packEffectiveDate,
        description: packDescription,
        rules_config: config,
        is_active: true,
      })
      setShowNewPackModal(false)
      setPackCode("")
      setPackName("")
      await loadData()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const handleCreatePolicy = async (e: FormEvent) => {
    e.preventDefault()
    if (!policyPool) return
    setActionLoading(true)
    try {
      await createReservePolicy({
        pool: policyPool,
        reserve_type: reserveType,
        regulatory_ceiling_pct: regulatoryCeiling,
        board_approved_target_pct: boardTarget,
        effective_from: policyEffectiveFrom,
      })
      setShowPolicyModal(false)
      await loadData()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const policyColumns: TableColumn<ReservePolicy>[] = [
    {
      header: "Pool",
      accessor: (p) => (
        <div>
          <p className="font-semibold text-sm text-ink-primary">{p.pool_name || p.pool}</p>
          <span className="text-xs text-ink-secondary">{p.pool_code}</span>
        </div>
      ),
    },
    {
      header: "Reserve Type",
      accessor: (p) => (
        <Badge variant={p.reserve_type === "per" ? "emerald" : "gold"}>
          {p.reserve_type.toUpperCase()} ({p.reserve_type === "per" ? "Profit Equalization" : "Investment Risk"})
        </Badge>
      ),
    },
    {
      header: "Regulatory Ceiling",
      accessor: (p) => `${p.regulatory_ceiling_pct}% max`,
    },
    {
      header: "Board Target",
      accessor: (p) => `${p.board_approved_target_pct}%`,
    },
    {
      header: "Current Balance",
      accessor: (p) => `PKR ${Number(p.current_balance).toLocaleString()}`,
    },
    {
      header: "Effective From",
      accessor: (p) => p.effective_from,
    },
    {
      header: "Status",
      accessor: (p) => (
        <Badge variant={p.is_active ? "emerald" : "neutral"}>
          {p.is_active ? "ACTIVE" : "INACTIVE"}
        </Badge>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      {!hideHeader && (
        <PageHeader
          screenNumber="42"
          title="42. Jurisdiction & Rule Packs"
          subtitle="Regulatory Framework Configurations, Multi-Jurisdiction Islamic Banking Standards, and PER/IRR Ceilings"
          actions={
            <div className="flex items-center gap-3">
              {canManage && (
                <>
                  <Button variant="secondary" onClick={() => setShowPolicyModal(true)}>
                    + Configure Reserve Policy
                  </Button>
                  <Button variant="primary" onClick={() => setShowNewPackModal(true)}>
                    + Add Custom Rule Pack
                  </Button>
                </>
              )}
            </div>
          }
        />
      )}

      {error && (
        <div className="rounded border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading regulatory rule packs...</span>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Configured Rule Packs"
              value={String(rulePacks.length)}
              deltaTone="neutral"
            />
            <StatCard
              label="Default Regulatory Engine"
              value={rulePacks.find((p) => p.is_default)?.code || "PK-SBP-2025"}
              deltaTone="positive"
            />
            <StatCard
              label="Active Reserve Policies"
              value={String(reservePolicies.filter((p) => p.is_active).length)}
              deltaTone="neutral"
            />
            <StatCard
              label="Jurisdictional Compliance"
              value="100% SBP / AAOIFI"
              deltaTone="positive"
            />
          </div>

          {/* Rule Packs Grid */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {rulePacks.map((pack) => {
              const cfg = pack.rules_config as Record<string, unknown>
              return (
                <div
                  key={pack.id}
                  className={`rounded-xl border p-5 transition ${
                    pack.is_default
                      ? "border-emerald-500/60 bg-emerald-950/10 shadow-lg shadow-emerald-950/20"
                      : "border-navy-700 bg-navy-900/60"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-ink-primary">{pack.name}</h3>
                        {pack.is_default && <Badge variant="emerald">DEFAULT JURISDICTION</Badge>}
                        {pack.is_active && !pack.is_default && <Badge variant="gold">ACTIVE</Badge>}
                      </div>
                      <span className="font-mono text-xs text-ink-secondary">
                        {pack.code} • Version {pack.version} (Effective: {pack.effective_date})
                      </span>
                    </div>
                  </div>

                  <p className="mt-3 text-xs text-ink-secondary">{pack.description}</p>

                  <div className="mt-4 grid grid-cols-2 gap-3 rounded-lg border border-navy-700 bg-navy-900/80 p-3 text-xs">
                    <div>
                      <span className="text-ink-muted">PER Ceiling:</span>
                      <p className="font-semibold text-ink-primary">
                        {String(cfg.per_ceiling_pct ?? "2.0")}% of net income
                      </p>
                    </div>
                    <div>
                      <span className="text-ink-muted">IRR Ceiling:</span>
                      <p className="font-semibold text-ink-primary">
                        {String(cfg.irr_ceiling_pct ?? "5.0")}% of pool assets
                      </p>
                    </div>
                    <div>
                      <span className="text-ink-muted">Notice Period:</span>
                      <p className="font-semibold text-ink-primary">
                        {String(cfg.notice_period_days ?? "30")} days
                      </p>
                    </div>
                    <div>
                      <span className="text-ink-muted">Mudarib Fee Cap:</span>
                      <p className="font-semibold text-ink-primary">
                        {String(cfg.mudarib_share_cap_pct ?? "20.0")}%
                      </p>
                    </div>
                  </div>

                  {canManage && (
                    <div className="mt-4 flex items-center justify-end gap-2">
                      {!pack.is_default && (
                        <Button
                          variant="secondary"
                          className="text-xs"
                          disabled={actionLoading}
                          onClick={() => handleActivatePack(pack.id, true)}
                        >
                          Set as Default
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Reserve Policies Table */}
          <Card
            title="Pool Reserve Policies (PER & IRR Ceilings)"
            actions={
              canManage && (
                <Button variant="secondary" className="text-xs" onClick={() => setShowPolicyModal(true)}>
                  + Add Policy
                </Button>
              )
            }
          >
            {reservePolicies.length > 0 ? (
              <Table
                columns={policyColumns}
                data={reservePolicies}
                keyField={(p) => p.id}
              />
            ) : (
              <div className="rounded border border-dashed border-navy-700 p-8 text-center text-sm text-ink-muted">
                No pool-specific reserve policies defined yet. System uses default statutory ceilings (2% PER, 5% IRR).
              </div>
            )}
          </Card>
        </>
      )}

      {/* New Rule Pack Modal */}
      {showNewPackModal && (
        <Modal
          isOpen={showNewPackModal}
          onClose={() => setShowNewPackModal(false)}
          title="Create Jurisdiction Rule Pack"
        >
          <form onSubmit={handleCreatePack} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Rule Pack Code *</label>
                <input
                  type="text"
                  value={packCode}
                  onChange={(e) => setPackCode(e.target.value)}
                  placeholder="e.g. CBUAE-IF-2025"
                  required
                  className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Version *</label>
                <input
                  type="text"
                  value={packVersion}
                  onChange={(e) => setPackVersion(e.target.value)}
                  required
                  className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Name *</label>
              <input
                type="text"
                value={packName}
                onChange={(e) => setPackName(e.target.value)}
                placeholder="e.g. Central Bank UAE Islamic Governance"
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Effective Date *</label>
              <input
                type="date"
                value={packEffectiveDate}
                onChange={(e) => setPackEffectiveDate(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Description</label>
              <textarea
                rows={2}
                value={packDescription}
                onChange={(e) => setPackDescription(e.target.value)}
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Rules Configuration (JSON) *</label>
              <textarea
                rows={6}
                value={packConfigJson}
                onChange={(e) => setPackConfigJson(e.target.value)}
                required
                className="mt-1 w-full rounded font-mono border border-navy-700 bg-navy-900 px-3 py-2 text-xs text-ink-primary"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button type="button" variant="secondary" onClick={() => setShowNewPackModal(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={actionLoading}>
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Save Rule Pack"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* New Policy Modal */}
      {showPolicyModal && (
        <Modal
          isOpen={showPolicyModal}
          onClose={() => setShowPolicyModal(false)}
          title="Configure Pool Reserve Policy (PER / IRR)"
        >
          <form onSubmit={handleCreatePolicy} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Target Pool *</label>
              <select
                value={policyPool}
                onChange={(e) => setPolicyPool(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              >
                {pools.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Reserve Type *</label>
              <select
                value={reserveType}
                onChange={(e) => setReserveType(e.target.value as "per" | "irr")}
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              >
                <option value="per">PER — Profit Equalization Reserve (Pre-Mudarib)</option>
                <option value="irr">IRR — Investment Risk Reserve (Post-Mudarib)</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Regulatory Ceiling % *</label>
                <input
                  type="number"
                  step="0.01"
                  value={regulatoryCeiling}
                  onChange={(e) => setRegulatoryCeiling(e.target.value)}
                  required
                  className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Board Approved Target % *</label>
                <input
                  type="number"
                  step="0.01"
                  value={boardTarget}
                  onChange={(e) => setBoardTarget(e.target.value)}
                  required
                  className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Effective From *</label>
              <input
                type="date"
                value={policyEffectiveFrom}
                onChange={(e) => setPolicyEffectiveFrom(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button type="button" variant="secondary" onClick={() => setShowPolicyModal(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={actionLoading}>
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Save Policy"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Bottom Control Total Bar matching Catalogue Screen 42 */}
      <div className="mt-6 border-t border-white/8 pt-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">
              RULE PACKS ACTIVE
            </p>
            <p className="text-base font-bold text-ink-primary">
              {rulePacks.filter((p) => p.is_active).length} <span className="text-emerald-400 text-xs">100%</span>
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">STANDARDS COVERED</p>
            <p className="text-base font-bold text-emerald-400">SBP • AAOIFI • BNM</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">RESERVE POLICIES</p>
            <p className="text-base font-bold text-emerald-400">{reservePolicies.length} Active</p>
          </div>
        </div>
      </div>
    </div>
  )
}
