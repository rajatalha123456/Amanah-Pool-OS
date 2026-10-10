import { useCallback, useEffect, useMemo, useState } from "react"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { extractErrorMessage } from "../api/errors"
import {
  fetchParticipantAccounts,
  fetchParticipants,
  rejectParticipantKyc,
  verifyParticipantKyc,
} from "../api/participants"
import type { BadgeVariant, Participant, ParticipantAccount } from "../types"

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
  const [participants, setParticipants] = useState<Participant[]>([])
  const [accounts, setAccounts] = useState<ParticipantAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [p, a] = await Promise.all([fetchParticipants(), fetchParticipantAccounts()])
      setParticipants(p)
      setAccounts(a)
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load participants."))
    } finally {
      setLoading(false)
    }
  }, [])

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
      <Card title={`Participant Registry (${participants.length})`}>
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-ink-secondary">
            <Spinner />
            <span className="text-sm">Loading participants...</span>
          </div>
        ) : (
          <Table columns={columns} data={participants} keyField={(p) => p.id} />
        )}
      </Card>
    </div>
  )
}
