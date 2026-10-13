import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { extractErrorMessage } from "../api/errors"
import {
  approveConfigChange,
  createApprovalRule,
  fetchConfigChanges,
  rejectConfigChange,
  type ConfigChange,
  fetchAccountCatalog,
  fetchAccountMappings,
  fetchApprovalActions,
  fetchApprovalRules,
  saveAccountMapping,
  updateApprovalRule,
  type AccountCatalogRow,
  type AccountMappingRow,
  type ApprovalRule,
} from "../api/governanceConfig"
import { USER_ROLES } from "../types"

const field =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

const APPROVER_ROLES = USER_ROLES.filter(
  (role) => !["investor_member", "platform_super_admin", "auditor"].includes(role),
)

/**
 * Approval matrix (owned by Risk & Compliance) and accounting mapping (owned by Finance).
 * Both are required before a pool can be activated (BR-001); changes are audited and rules are
 * deactivated rather than deleted.
 */
const KIND_LABEL: Record<string, string> = {
  approval_matrix: "Approval matrix",
  account_mapping: "Account mapping",
  reserve_policy: "Reserve policy (PER / IRR)",
  rule_pack: "Jurisdiction rule pack",
}

function show(value: unknown): string {
  return value !== null && typeof value === "object" ? JSON.stringify(value) : String(value)
}

export function GovernanceConfig() {
  const { user } = useAuth()
  const role = user?.role ?? ""
  const canEditMatrix = role === "risk_compliance" || role === "platform_super_admin"
  const canEditMapping = role === "finance_maker" || role === "finance_checker" || role === "platform_super_admin"
  const canDecide = role === "finance_checker" || role === "authorized_signatory"

  const [rules, setRules] = useState<ApprovalRule[]>([])
  const [actions, setActions] = useState<Array<{ key: string; label: string }>>([])
  const [mappings, setMappings] = useState<AccountMappingRow[]>([])
  const [catalog, setCatalog] = useState<AccountCatalogRow[]>([])
  const [changes, setChanges] = useState<ConfigChange[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const [ruleForm, setRuleForm] = useState({ action: "", role: "", max_amount: "", reason: "" })
  const [mapForm, setMapForm] = useState({ account_key: "", gl_code: "", gl_name: "", reason: "" })

  const load = useCallback(async () => {
    try {
      const [r, a, m, c, ch] = await Promise.all([
        fetchApprovalRules(),
        fetchApprovalActions(),
        fetchAccountMappings(),
        fetchAccountCatalog(),
        fetchConfigChanges(),
      ])
      setChanges(ch)
      setRules(r)
      setActions(a)
      setMappings(m)
      setCatalog(c)
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load governance configuration."))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function act(action: () => Promise<unknown>, after?: () => void) {
    setBusy(true)
    setError("")
    try {
      await action()
      after?.()
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "The change was rejected."))
    } finally {
      setBusy(false)
    }
  }

  const actionLabel = (key: string) => actions.find((a) => a.key === key)?.label ?? key
  const tenantDefaults = useMemo(() => mappings.filter((m) => !m.pool), [mappings])
  const mappedKeys = new Set(tenantDefaults.map((m) => m.account_key))

  const ruleColumns: TableColumn<ApprovalRule>[] = [
    { header: "Approval", accessor: (r) => actionLabel(r.action) },
    { header: "Role", accessor: (r) => r.role },
    {
      header: "Limit (PKR)",
      accessor: (r) => (r.max_amount === null ? "Unlimited" : Number(r.max_amount).toLocaleString()),
    },
    {
      header: "Status",
      accessor: (r) => <Badge variant={r.is_active ? "emerald" : "neutral"}>{r.is_active ? "active" : "inactive"}</Badge>,
    },
    {
      header: "",
      accessor: (r) =>
        canEditMatrix ? (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => {
              const change_reason = window.prompt("Reason for this change (it goes to a checker for approval)")
              if (change_reason) void act(() => updateApprovalRule(r.id, { is_active: !r.is_active, change_reason }))
            }}
          >
            {r.is_active ? "Deactivate" : "Activate"}
          </Button>
        ) : null,
    },
  ]

  const mappingColumns: TableColumn<AccountMappingRow>[] = [
    { header: "Logical account", accessor: (m) => m.account_key },
    { header: "GL code", accessor: (m) => <span className="font-mono">{m.gl_code}</span> },
    { header: "GL account name", accessor: (m) => m.gl_name },
    { header: "Scope", accessor: (m) => (m.pool_code ? `Pool ${m.pool_code}` : "Tenant default") },
  ]

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner /> <span className="text-sm">Loading...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Governance Configuration"
        subtitle="Approval matrix and accounting mapping - both are required before a pool can be activated (BR-001)"
      />
      {error && <p className="rounded-md border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-300">{error}</p>}

      <Card title="Changes awaiting approval">
        <p className="mb-3 text-xs text-ink-secondary">
          Matrix, mapping, reserve policy and rule pack edits are proposals. A different person (a finance checker; for a rule pack also the authorized signatory) must approve them before they take effect.
        </p>
        {changes.filter((c) => c.status === "pending").length === 0 ? (
          <p className="text-sm text-ink-secondary">Nothing pending.</p>
        ) : (
          <div className="space-y-2">
            {changes
              .filter((c) => c.status === "pending")
              .map((c) => (
                <div key={c.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs">
                  <p className="font-semibold text-ink-primary">
                    {KIND_LABEL[c.kind] ?? c.kind} · {c.operation} · by{" "}
                    {c.requested_by_name ?? "—"}
                  </p>
                  <p className="mt-1 font-mono text-[11px] text-ink-secondary">
                    {Object.entries(c.payload)
                      .map(([k, v]) => `${k}: ${c.before[k] !== undefined ? `${show(c.before[k])} → ` : ""}${show(v)}`)
                      .join(" · ")}
                  </p>
                  <p className="mt-1 text-ink-secondary">Reason: {c.reason}</p>
                  {canDecide && String(c.requested_by) !== String(user?.id) && (
                    <div className="mt-2 flex gap-4">
                      <button type="button" disabled={busy} className="text-emerald-400" onClick={() => void act(() => approveConfigChange(c.id))}>
                        Approve
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        className="text-red-400"
                        onClick={() => {
                          const reason = window.prompt("Reason for rejection")
                          if (reason) void act(() => rejectConfigChange(c.id, reason))
                        }}
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              ))}
          </div>
        )}
      </Card>

      <Card title="Approval matrix">
        <p className="mb-3 text-xs text-ink-secondary">
          Once an approval has rules, only the listed roles may give it and only up to their limit. Owned by Risk &amp;
          Compliance.
        </p>
        <Table columns={ruleColumns} data={rules} keyField={(r) => r.id} />
        {canEditMatrix && (
          <form
            className="mt-4 flex flex-wrap items-end gap-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
              void act(
                () =>
                  createApprovalRule({
                    action: ruleForm.action,
                    role: ruleForm.role,
                    max_amount: ruleForm.max_amount ? ruleForm.max_amount : null,
                    change_reason: ruleForm.reason,
                  }),
                () => setRuleForm({ action: "", role: "", max_amount: "", reason: "" }),
              )
            }}
          >
            <select required className={field} value={ruleForm.action} onChange={(e) => setRuleForm({ ...ruleForm, action: e.target.value })}>
              <option value="">Approval...</option>
              {actions.map((a) => (
                <option key={a.key} value={a.key}>
                  {a.label}
                </option>
              ))}
            </select>
            <select required className={field} value={ruleForm.role} onChange={(e) => setRuleForm({ ...ruleForm, role: e.target.value })}>
              <option value="">Role...</option>
              {APPROVER_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Limit (empty = unlimited)"
              className={field}
              value={ruleForm.max_amount}
              onChange={(e) => setRuleForm({ ...ruleForm, max_amount: e.target.value })}
            />
            <input required placeholder="Reason for change" className={`${field} w-56`} value={ruleForm.reason} onChange={(e) => setRuleForm({ ...ruleForm, reason: e.target.value })} />
            <Button type="submit" variant="primary" disabled={busy}>
              Add rule
            </Button>
          </form>
        )}
      </Card>

      <Card title="Accounting mapping (logical account → enterprise GL)">
        <p className="mb-3 text-xs text-ink-secondary">
          Journals are named from this mapping when posted; already-posted journals keep their original names. Owned by
          Finance.
        </p>
        <div className="mb-3 flex flex-wrap gap-2 text-xs">
          {catalog
            .filter((c) => c.required_for.length > 0)
            .map((c) => (
              <Badge key={c.key} variant={mappedKeys.has(c.key) ? "emerald" : "gold"}>
                {c.key}
                {mappedKeys.has(c.key) ? "" : " - unmapped"}
              </Badge>
            ))}
        </div>
        <Table columns={mappingColumns} data={mappings} keyField={(m) => m.id} />
        {canEditMapping && (
          <form
            className="mt-4 flex flex-wrap items-end gap-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
              const existing = tenantDefaults.find((m) => m.account_key === mapForm.account_key)
              void act(
                () =>
                  saveAccountMapping(
                    { account_key: mapForm.account_key, gl_code: mapForm.gl_code, gl_name: mapForm.gl_name, change_reason: mapForm.reason },
                    existing?.id,
                  ),
                () => setMapForm({ account_key: "", gl_code: "", gl_name: "", reason: "" }),
              )
            }}
          >
            <select required className={field} value={mapForm.account_key} onChange={(e) => setMapForm({ ...mapForm, account_key: e.target.value })}>
              <option value="">Logical account...</option>
              {catalog.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.key}
                </option>
              ))}
            </select>
            <input required placeholder="GL code" className={field} value={mapForm.gl_code} onChange={(e) => setMapForm({ ...mapForm, gl_code: e.target.value })} />
            <input required placeholder="GL account name" className={`${field} w-72`} value={mapForm.gl_name} onChange={(e) => setMapForm({ ...mapForm, gl_name: e.target.value })} />
            <input required placeholder="Reason for change" className={`${field} w-56`} value={mapForm.reason} onChange={(e) => setMapForm({ ...mapForm, reason: e.target.value })} />
            <Button type="submit" variant="primary" disabled={busy}>
              Propose mapping
            </Button>
          </form>
        )}
      </Card>
    </div>
  )
}
