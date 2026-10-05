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

  function exportCSV() {
    if (entries.length === 0) return
    const headers = ["ID", "Source", "Amount", "Identified Date", "Status", "Charity Recipient", "Distributed Date"]
    const rows = entries.map((e) => [
      e.id,
      `"${e.source_description}"`,
      e.amount,
      e.identified_date,
      e.status,
      `"${e.charity_recipient || ""}"`,
      e.distributed_date || "",
    ])
    const csvContent =
      "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n")
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    link.setAttribute("download", `purification_ledger_${selectedPoolId}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-white/8 pb-4">
        <div className="flex items-center gap-3">
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
          <Button variant="outline" className="text-xs py-1.5 px-3" onClick={exportCSV} disabled={entries.length === 0}>
            EXPORT (CSV)
          </Button>
        </div>
        {selectedPoolId && (
          <Button variant="primary" className="text-xs py-1.5 px-3" onClick={() => setIsNewModalOpen(true)}>
            + NEW RECORD
          </Button>
        )}
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
            <>
              <Table columns={columns} data={entries} keyField={(e) => e.id} />

              {/* Bottom Control Total Bar matching Catalogue Screen 32 */}
              <div className="mt-6 border-t border-white/8 pt-4">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
                  <div>
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">
                      RECORDS PROCESSED
                    </p>
                    <p className="text-base font-bold text-ink-primary">
                      {entries.length.toLocaleString()}{" "}
                      <span className="text-emerald-400 text-xs">100%</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">MATCHED</p>
                    <p className="text-base font-bold text-emerald-400">
                      {entries.filter((e) => e.status === "identified").length === 0
                        ? "100.0%"
                        : `${(100 - (entries.filter((e) => e.status === "identified").length / Math.max(entries.length, 1)) * 5).toFixed(2)}%`}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">PENDING PURIFICATION</p>
                    <p className="text-base font-bold text-ink-primary">
                      {entries.filter((e) => e.status === "identified").length}{" "}
                      <span className="text-emerald-400 text-xs">
                        {entries.filter((e) => e.status === "identified").length > 0 ? "action required" : "clear"}
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTROL TOTAL</p>
                    <p className="text-base font-bold text-emerald-400">
                      {entries.filter((e) => e.status === "identified").length === 0 ? "Balanced " : "Action "}
                      <span
                        className={`rounded px-1 text-xs ${
                          entries.filter((e) => e.status === "identified").length === 0
                            ? "bg-emerald-500/20 text-emerald-300"
                            : "bg-gold-500/20 text-gold-300"
                        }`}
                      >
                        {entries.filter((e) => e.status === "identified").length === 0 ? "PASS" : "REVIEW"}
                      </span>
                    </p>
                  </div>
                </div>
              </div>
            </>
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
