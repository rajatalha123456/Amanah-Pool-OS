import { useCallback, useEffect, useMemo, useState } from "react"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Modal } from "../components/Modal"
import { PageHeader } from "../components/PageHeader"
import { Pager } from "../components/Pager"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { extractErrorMessage } from "../api/errors"
import { DEFAULT_PAGE_SIZE } from "../api/pagination"
import { fetchPools } from "../api/pools"
import {
  createParticipant,
  createParticipantAccount,
  linkParticipantLogin,
  fetchAccountsOfParticipants,
  fetchParticipants,
  rejectParticipantKyc,
  verifyParticipantKyc,
} from "../api/participants"
import type { BadgeVariant, Participant, ParticipantAccount, Pool } from "../types"

const KYC_BADGE: Record<string, BadgeVariant> = {
  verified: "emerald",
  pending: "gold",
  rejected: "navy",
}

/**
 * Participant registry (BRD Section 11: Participant / CapitalAccount).
 * Profit is allocated and statements are issued per participant account;
 * KYC must be verified by Risk & Compliance before balances can be imported.
 */
export function ParticipantRegistry() {
  const { user } = useAuth()
  const canDecideKyc = user?.role === "risk_compliance"
  const canEdit = user?.role === "pool_manager" || user?.role === "finance_maker"
  const canLink = user?.role === "pool_manager"
  const [pools, setPools] = useState<Pool[]>([])
  const [dialog, setDialog] = useState<null | { kind: "participant" } | { kind: "account" | "login"; p: Participant }>(null)
  const [form, setForm] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState("")
  const field = (k: string) => form[k] ?? ""
  const setField = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  function openDialog(d: NonNullable<typeof dialog>) {
    setForm({ tax_status: "filer", participant_type: "individual", opened_date: new Date().toISOString().slice(0, 10) })
    setFormError("")
    setDialog(d)
    if (d.kind === "account") void fetchPools().then(setPools).catch(() => setPools([]))
  }

  async function submitDialog() {
    if (!dialog) return
    try {
      if (dialog.kind === "participant") {
        await createParticipant({
          reference: field("reference"), full_name: field("full_name"), participant_class: field("participant_class"),
          email: field("email"), cnic_ntn: field("cnic_ntn"), iban: field("iban"), bank_name: field("bank_name"),
          tax_status: field("tax_status"), participant_type: field("participant_type") || "individual",
          registration_number: field("registration_number"), nominee_name: field("nominee_name"),
          nominee_cnic: field("nominee_cnic"), nominee_relationship: field("nominee_relationship"),
        })
      } else if (dialog.kind === "account") {
        await createParticipantAccount({
          participant: dialog.p.id, pool: field("pool"), account_number: field("account_number"), opened_date: field("opened_date"),
        })
      } else {
        await linkParticipantLogin(dialog.p.id, field("email"))
      }
      setDialog(null)
      await load()
    } catch (err) {
      setFormError(extractErrorMessage(err, "Could not save."))
    }
  }
  const [participants, setParticipants] = useState<Participant[]>([])
  const [accounts, setAccounts] = useState<ParticipantAccount[]>([])
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const p = await fetchParticipants(page)
      setParticipants(p.results)
      setCount(p.count)
      setAccounts(await fetchAccountsOfParticipants(p.results.map((x) => x.id)))
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load participants."))
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    void load()
  }, [load])

  const accountsByParticipant = useMemo(() => {
    const map = new Map<string, ParticipantAccount[]>()
    for (const account of accounts) {
      map.set(account.participant, [...(map.get(account.participant) ?? []), account])
    }
    return map
  }, [accounts])

  async function decide(participant: Participant, approve: boolean) {
    setBusyId(participant.id)
    try {
      await (approve ? verifyParticipantKyc(participant.id) : rejectParticipantKyc(participant.id))
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "KYC decision failed."))
    } finally {
      setBusyId(null)
    }
  }

  const columns: TableColumn<Participant>[] = [
    { header: "Reference", accessor: (p) => p.reference },
    { header: "Name", accessor: (p) => p.full_name },
    { header: "Class", accessor: (p) => p.participant_class },
    {
      header: "Accounts",
      accessor: (p) => (accountsByParticipant.get(p.id) ?? []).map((a) => a.account_number).join(", ") || "—",
    },
    {
      header: "KYC",
      accessor: (p) => <Badge variant={KYC_BADGE[p.kyc_status] ?? "neutral"}>{p.kyc_status}</Badge>,
    },
    { header: "Tax", accessor: (p) => p.tax_status },
    {
      header: "Login",
      accessor: (p) =>
        p.user ? (
          "linked"
        ) : canLink ? (
          <Button variant="secondary" onClick={() => openDialog({ kind: "login", p })}>Link login</Button>
        ) : (
          "—"
        ),
    },
    {
      header: "Accounts +",
      accessor: (p) =>
        canEdit ? <Button variant="secondary" onClick={() => openDialog({ kind: "account", p })}>Add account</Button> : "—",
    },
    {
      header: "Action",
      accessor: (p) =>
        canDecideKyc && p.kyc_status !== "verified" ? (
          <div className="flex gap-2">
            <Button variant="primary" disabled={busyId === p.id} onClick={() => decide(p, true)}>
              Verify
            </Button>
            <Button variant="secondary" disabled={busyId === p.id} onClick={() => decide(p, false)}>
              Reject
            </Button>
          </div>
        ) : (
          "—"
        ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Participants"
        subtitle="Depositors and investors with their pool accounts and KYC status"
      />
      {error && <p className="text-sm text-red-400">{error}</p>}
      {canEdit && (
        <div>
          <Button variant="primary" onClick={() => openDialog({ kind: "participant" })}>New participant</Button>
        </div>
      )}
      {dialog && (
        <Modal
          title={dialog.kind === "participant" ? "New participant" : dialog.kind === "account" ? `Add account - ${dialog.p.full_name}` : `Link login - ${dialog.p.full_name}`}
          onClose={() => setDialog(null)}
        >
          <div className="space-y-3">
            {dialog.kind === "participant" && (
              <>
                {[["reference", "Reference"], ["full_name", "Full name"], ["participant_class", "Class (e.g. Retail Regular)"],
                  ["email", "Email"], ["cnic_ntn", "CNIC / NTN"], ["iban", "IBAN"], ["bank_name", "Bank name"]].map(([k, label]) => (
                  <label key={k} className="block text-sm">
                    {label}
                    <input className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field(k)} onChange={(e) => setField(k, e.target.value)} />
                  </label>
                ))}
                <label className="block text-sm">
                  Type
                  <select className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field("participant_type")} onChange={(e) => setField("participant_type", e.target.value)}>
                    <option value="individual">Individual (KYC)</option>
                    <option value="company">Company (KYB)</option>
                  </select>
                </label>
                {field("participant_type") === "company" && (
                  <label className="block text-sm">
                    Company registration number (required for KYB)
                    <input className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field("registration_number")} onChange={(e) => setField("registration_number", e.target.value)} />
                  </label>
                )}
                {[["nominee_name", "Nominee name"], ["nominee_cnic", "Nominee CNIC"], ["nominee_relationship", "Nominee relationship"]].map(([k, label]) => (
                  <label key={k} className="block text-sm">
                    {label}
                    <input className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field(k)} onChange={(e) => setField(k, e.target.value)} />
                  </label>
                ))}
                <label className="block text-sm">
                  Tax status
                  <select className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field("tax_status")} onChange={(e) => setField("tax_status", e.target.value)}>
                    <option value="filer">Filer</option>
                    <option value="non_filer">Non-filer</option>
                  </select>
                </label>
              </>
            )}
            {dialog.kind === "account" && (
              <>
                <label className="block text-sm">
                  Pool
                  <select className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field("pool")} onChange={(e) => setField("pool", e.target.value)}>
                    <option value="">Select a pool</option>
                    {pools.map((pl) => <option key={pl.id} value={pl.id}>{pl.name}</option>)}
                  </select>
                </label>
                <label className="block text-sm">
                  Account number
                  <input className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field("account_number")} onChange={(e) => setField("account_number", e.target.value)} />
                </label>
                <label className="block text-sm">
                  Opened on
                  <input type="date" className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field("opened_date")} onChange={(e) => setField("opened_date", e.target.value)} />
                </label>
              </>
            )}
            {dialog.kind === "login" && (
              <label className="block text-sm">
                Email of the investor login (create it first in Administration, role Investor / member)
                <input className="mt-1 w-full rounded border border-line bg-transparent p-2" value={field("email")} onChange={(e) => setField("email", e.target.value)} />
              </label>
            )}
            {formError && <p className="text-sm text-red-400">{formError}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDialog(null)}>Cancel</Button>
              <Button variant="primary" onClick={() => void submitDialog()}>Save</Button>
            </div>
          </div>
        </Modal>
      )}
      <Card title={`Participant Registry (${count})`}>
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-ink-secondary">
            <Spinner />
            <span className="text-sm">Loading participants...</span>
          </div>
        ) : (
          <>
            <Table columns={columns} data={participants} keyField={(p) => p.id} />
            <Pager page={page} pageSize={DEFAULT_PAGE_SIZE} count={count} onChange={setPage} />
          </>
        )}
      </Card>
    </div>
  )
}
