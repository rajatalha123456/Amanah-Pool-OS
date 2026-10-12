import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import {
  approveProvision,
  fetchAssets,
  fetchAssetPosition,
  fetchProvisions,
  rejectProvision,
  requestProvision,
} from "../api/assets"
import { extractErrorMessage } from "../api/errors"
import type { Asset, AssetPosition, AssetProvisionEntry, BadgeVariant } from "../types"

const TYPE_LABEL: Record<string, string> = {
  provision: "Provision",
  release: "Provision release",
  write_off: "Write-off",
  recovery: "Recovery",
}
const STATUS_BADGE: Record<string, BadgeVariant> = { pending: "gold", approved: "emerald", rejected: "navy" }
const INPUT =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

const money = (v: string) => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })

/** Maker-checker provisions, write-offs and recoveries on assets (BRD 6.4). */
export function AssetProvisions() {
  const { user } = useAuth()
  const role = user?.role ?? ""
  const canRequest = role === "finance_maker" || role === "pool_manager"
  const canDecide = role === "finance_checker"

  const [entries, setEntries] = useState<AssetProvisionEntry[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [position, setPosition] = useState<AssetPosition | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ asset: "", entry_type: "provision", amount: "", effective_date: "", reason: "" })

  const load = useCallback(async () => {
    try {
      const [rows, assetRows] = await Promise.all([fetchProvisions(), fetchAssets()])
      setEntries(rows)
      setAssets(assetRows)
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load provisions."))
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!form.asset) {
      setPosition(null)
      return
    }
    fetchAssetPosition(form.asset)
      .then(setPosition)
      .catch(() => setPosition(null))
  }, [form.asset, entries])

  async function act(action: () => Promise<unknown>, after?: () => void) {
    setBusy(true)
    setError("")
    try {
      await action()
      after?.()
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "The action failed."))
    } finally {
      setBusy(false)
    }
  }

  const columns: TableColumn<AssetProvisionEntry>[] = [
    { header: "Date", accessor: (e) => e.effective_date },
    { header: "Asset", accessor: (e) => `${e.asset_reference} (${e.pool_code})` },
    { header: "Type", accessor: (e) => TYPE_LABEL[e.entry_type] ?? e.entry_type },
    { header: "Amount", accessor: (e) => money(e.amount) },
    { header: "Maker", accessor: (e) => e.created_by_name ?? "—" },
    { header: "Reason", accessor: (e) => e.rejection_reason ? `${e.reason} (rejected: ${e.rejection_reason})` : e.reason },
    { header: "Status", accessor: (e) => <Badge variant={STATUS_BADGE[e.status] ?? "neutral"}>{e.status}</Badge> },
    {
      header: "",
      accessor: (e) =>
        canDecide && e.status === "pending" ? (
          <div className="flex gap-3">
            <button
              type="button"
              disabled={busy}
              className="text-sm font-medium text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
              onClick={() => void act(() => approveProvision(e.id))}
            >
              Approve
            </button>
            <button
              type="button"
              disabled={busy}
              className="text-sm font-medium text-red-400 hover:text-red-300 disabled:opacity-50"
              onClick={() => {
                const reason = window.prompt("Reason for rejection")
                if (reason) void act(() => rejectProvision(e.id, reason))
              }}
            >
              Reject
            </button>
          </div>
        ) : null,
    },
  ]

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-400">{error}</p>}

      {canRequest && (
        <Card title="Request provision / write-off / recovery">
          <form
            className="grid grid-cols-1 gap-3 sm:grid-cols-2"
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
              void act(
                () => requestProvision(form),
                () => setForm({ ...form, amount: "", reason: "" }),
              )
            }}
          >
            <select required className={INPUT} value={form.asset} onChange={(e) => setForm({ ...form, asset: e.target.value })}>
              <option value="">Select asset</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.reference_code} - {a.asset_type} ({a.status})
                </option>
              ))}
            </select>
            <select className={INPUT} value={form.entry_type} onChange={(e) => setForm({ ...form, entry_type: e.target.value })}>
              {Object.entries(TYPE_LABEL).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <input required type="number" step="0.01" min="0.01" placeholder="Amount (PKR)" className={INPUT} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            <input required type="date" className={INPUT} value={form.effective_date} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} />
            <textarea required rows={2} placeholder="Reason / evidence reference" className={`${INPUT} sm:col-span-2`} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            {position && (
              <p className="text-xs text-ink-secondary sm:col-span-2">
                Face {money(position.face_value)} · exposure {money(position.exposure)} · provision held{" "}
                {money(position.provision_balance)} · written off {money(position.written_off)} · still recoverable{" "}
                {money(position.recoverable_balance)}
              </p>
            )}
            <div className="sm:col-span-2">
              <Button type="submit" variant="primary" disabled={busy}>
                Submit for checker approval
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card title="Provision ledger">
        {entries.length === 0 ? (
          <p className="text-sm text-ink-secondary">No entries.</p>
        ) : (
          <Table columns={columns} data={entries} keyField={(e) => e.id} />
        )}
      </Card>
    </div>
  )
}
