import { useEffect, useState } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { fetchPools } from "../api/pools"
import { approvePurificationEntry, fetchPurificationEntries } from "../api/governance"
import { extractErrorMessage } from "../api/errors"
import { NewPurificationEntryModal } from "./governance/NewPurificationEntryModal"
import { MarkDistributedModal } from "./governance/MarkDistributedModal"
import type { BadgeVariant, Pool, PurificationEntry } from "../types"

type PageState = "loading" | "loaded" | "error"

const STATUS_BADGE: Record<string, BadgeVariant> = {
  identified: "neutral",
  approved_for_purification: "gold",
  distributed: "emerald",
}

function statusBadgeVariant(status: string): BadgeVariant {
  return STATUS_BADGE[status] ?? "neutral"
}

const selectClasses =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

export function PurificationLedger() {
  const { user } = useAuth()
  const canApprove = user?.role === "shariah_board"
  const canMarkDistributed = user?.role === "finance_checker"

  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState("")
  const [entries, setEntries] = useState<PurificationEntry[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [isNewModalOpen, setIsNewModalOpen] = useState(false)
  const [distributeEntry, setDistributeEntry] = useState<PurificationEntry | null>(null)
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        if (data.length > 0) {
          setSelectedPoolId(data[0].id)
        } else {
          setPageState("loaded")
        }
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load pools."))
        setPageState("error")
      })
  }, [])

  function loadEntries(poolId: string) {
    setPageState("loading")
    setPageError("")
    fetchPurificationEntries(poolId)
      .then((data) => {
        setEntries(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load purification entries."))
        setPageState("error")
      })
  }

  useEffect(() => {
    if (selectedPoolId) {
      loadEntries(selectedPoolId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPoolId])

  async function handleApprove(entry: PurificationEntry) {
    setActionErrors((prev) => ({ ...prev, [entry.id]: "" }))
    try {
      const updated = await approvePurificationEntry(entry.id)
      setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
    } catch (err) {
      setActionErrors((prev) => ({
        ...prev,
        [entry.id]: extractErrorMessage(err, "Unable to approve this entry."),
      }))
    }
  }

  function handleCreated(entry: PurificationEntry) {
    setEntries((prev) => [entry, ...prev])
    setIsNewModalOpen(false)
  }

  function handleDistributed(updated: PurificationEntry) {
    setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
    setDistributeEntry(null)
  }

  const columns: TableColumn<PurificationEntry>[] = [
    { header: "Source", accessor: (e) => e.source_description },
    { header: "Amount", accessor: (e) => e.amount },
    { header: "Identified", accessor: (e) => e.identified_date },
    {
      header: "Status",
      accessor: (e) => <Badge variant={statusBadgeVariant(e.status)}>{e.status}</Badge>,
    },
    {
      header: "Charity / Distributed",
      accessor: (e) =>
        e.status === "distributed" ? (
          <span className="text-xs text-ink-secondary">
            {e.charity_recipient} · {e.distributed_date}
          </span>
        ) : (
          "—"
        ),
    },
    {
      header: "Action",
      accessor: (e) => (
        <div className="flex flex-col gap-1">
          {e.status === "identified" && canApprove && (
            <Button variant="primary" onClick={() => handleApprove(e)}>
              Approve
            </Button>
          )}
          {e.status === "approved_for_purification" && canMarkDistributed && (
            <Button variant="primary" onClick={() => setDistributeEntry(e)}>
              Mark Distributed
            </Button>
          )}
          {actionErrors[e.id] && <p className="text-xs text-red-400">{actionErrors[e.id]}</p>}
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-secondary">
          Non-Shariah-compliant income tracked through identification, approval and charitable distribution
        </p>
        {selectedPoolId && (
          <Button variant="primary" onClick={() => setIsNewModalOpen(true)}>
            + New Entry
          </Button>
        )}
      </div>

      <div className="mb-4">
        <select
          value={selectedPoolId}
          onChange={(e) => setSelectedPoolId(e.target.value)}
          className={selectClasses}
        >
          {pools.map((pool) => (
            <option key={pool.id} value={pool.id}>
              {pool.code} — {pool.name}
            </option>
          ))}
        </select>
      </div>

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading purification entries...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <Card>
          {pools.length === 0 ? (
            <p className="text-sm text-ink-secondary">No pools available.</p>
          ) : entries.length === 0 ? (
            <p className="text-sm text-ink-secondary">No purification entries for this pool yet.</p>
          ) : (
            <Table columns={columns} data={entries} keyField={(e) => e.id} />
          )}
        </Card>
      )}

      {isNewModalOpen && selectedPoolId && (
        <NewPurificationEntryModal
          poolId={selectedPoolId}
          onClose={() => setIsNewModalOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {distributeEntry && (
        <MarkDistributedModal
          entry={distributeEntry}
          onClose={() => setDistributeEntry(null)}
          onDone={handleDistributed}
        />
      )}
    </div>
  )
}
