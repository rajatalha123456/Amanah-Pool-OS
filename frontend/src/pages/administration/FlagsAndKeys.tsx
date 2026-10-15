import { useCallback, useEffect, useState } from "react"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Card } from "../../components/Card"
import { Table, type TableColumn } from "../../components/Table"
import { extractErrorMessage } from "../../api/errors"
import {
  fetchEncryptionKeys,
  fetchFeatureFlags,
  recordKeyRotation,
  registerEncryptionKey,
  setFeatureFlag,
  toggleFeatureFlag,
  type EncryptionKeyRecord,
  type FeatureFlag,
} from "../../api/flagsAndKeys"
import { fetchTenants } from "../../api/tenants"

const input = "mt-1 w-full rounded border border-white/10 bg-transparent p-2 text-sm"

/** Feature flags per tenant and the register of encryption keys (metadata only: the key itself stays in the KMS/HSM). */
export function FlagsAndKeys() {
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [keys, setKeys] = useState<EncryptionKeyRecord[]>([])
  const [tenants, setTenants] = useState<{ id: string; code: string; name: string }[]>([])
  const [error, setError] = useState("")
  const [flagForm, setFlagForm] = useState({ tenant: "", key: "", note: "" })
  const [keyForm, setKeyForm] = useState({ tenant: "", purpose: "", provider: "", key_reference: "", rotation_interval_days: "365" })

  const load = useCallback(async () => {
    try {
      setFlags(await fetchFeatureFlags())
      setKeys(await fetchEncryptionKeys())
      setTenants(await fetchTenants())
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load."))
    }
  }, [])
  useEffect(() => { void load() }, [load])

  async function run(action: () => Promise<void>) {
    try { await action(); await load() } catch (err) { setError(extractErrorMessage(err, "Could not save.")) }
  }

  const flagColumns: TableColumn<FeatureFlag>[] = [
    { header: "Tenant", accessor: (f) => f.tenant_code },
    { header: "Feature", accessor: (f) => f.key },
    { header: "State", accessor: (f) => <Badge variant={f.enabled ? "emerald" : "neutral"}>{f.enabled ? "on" : "off"}</Badge> },
    { header: "Note", accessor: (f) => f.note || "-" },
    { header: "", accessor: (f) => <Button variant="secondary" onClick={() => run(() => toggleFeatureFlag(f.id, !f.enabled))}>Turn {f.enabled ? "off" : "on"}</Button> },
  ]
  const keyColumns: TableColumn<EncryptionKeyRecord>[] = [
    { header: "Tenant", accessor: (k) => k.tenant_code },
    { header: "Purpose", accessor: (k) => k.purpose },
    { header: "Held in", accessor: (k) => `${k.provider} (${k.key_reference})` },
    { header: "Last rotated", accessor: (k) => k.last_rotated_on ?? "never" },
    { header: "Next due", accessor: (k) => k.rotation_due_on ?? "-" },
    { header: "Status", accessor: (k) => <Badge variant={k.overdue ? "navy" : "emerald"}>{k.overdue ? "rotation overdue" : "in date"}</Badge> },
    { header: "", accessor: (k) => <Button variant="secondary" onClick={() => run(() => recordKeyRotation(k.id))}>Record rotation today</Button> },
  ]

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-400">{error}</p>}
      <Card title="Feature flags">
        <p className="mb-3 text-xs text-ink-secondary">A feature that has never been set is off. Every change is written to the audit log.</p>
        <div className="mb-4 grid gap-3 md:grid-cols-4">
          <label className="text-sm">Tenant
            <select className={input} value={flagForm.tenant} onChange={(e) => setFlagForm({ ...flagForm, tenant: e.target.value })}>
              <option value="">Select</option>
              {tenants.map((t) => <option key={t.id} value={t.id}>{t.code}</option>)}
            </select>
          </label>
          <label className="text-sm">Feature key<input className={input} value={flagForm.key} onChange={(e) => setFlagForm({ ...flagForm, key: e.target.value })} placeholder="e.g. urdu-disclosure" /></label>
          <label className="text-sm">Note<input className={input} value={flagForm.note} onChange={(e) => setFlagForm({ ...flagForm, note: e.target.value })} /></label>
          <div className="flex items-end"><Button variant="primary" onClick={() => run(() => setFeatureFlag({ ...flagForm, enabled: true }))}>Turn on</Button></div>
        </div>
        <Table columns={flagColumns} data={flags} keyField={(f) => f.id} />
      </Card>
      <Card title="Encryption key register">
        <p className="mb-3 text-xs text-ink-secondary">
          This lists where each key lives and when it was last rotated. It never holds a key. Recording a rotation here states that it was done in the bank's KMS/HSM.
        </p>
        <div className="mb-4 grid gap-3 md:grid-cols-5">
          <label className="text-sm">Tenant
            <select className={input} value={keyForm.tenant} onChange={(e) => setKeyForm({ ...keyForm, tenant: e.target.value })}>
              <option value="">Select</option>
              {tenants.map((t) => <option key={t.id} value={t.id}>{t.code}</option>)}
            </select>
          </label>
          <label className="text-sm">Purpose<input className={input} value={keyForm.purpose} onChange={(e) => setKeyForm({ ...keyForm, purpose: e.target.value })} /></label>
          <label className="text-sm">Provider<input className={input} value={keyForm.provider} onChange={(e) => setKeyForm({ ...keyForm, provider: e.target.value })} /></label>
          <label className="text-sm">Key reference<input className={input} value={keyForm.key_reference} onChange={(e) => setKeyForm({ ...keyForm, key_reference: e.target.value })} /></label>
          <div className="flex items-end"><Button variant="primary" onClick={() => run(() => registerEncryptionKey({ ...keyForm, rotation_interval_days: Number(keyForm.rotation_interval_days) }))}>Register key</Button></div>
        </div>
        <Table columns={keyColumns} data={keys} keyField={(k) => k.id} />
      </Card>
    </div>
  )
}
