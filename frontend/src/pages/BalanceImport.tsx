import { useEffect, useState, type FormEvent } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { fetchPools } from "../api/pools"
import { fetchImportHistory, importBalances } from "../api/balances"
import { extractErrorMessage } from "../api/errors"
import type { BadgeVariant, BalanceImportBatch, BalanceImportResult, Pool } from "../types"

interface RecordRow {
  participant_class: string
  balance_amount: string
}

const BATCH_STATUS_BADGE: Record<string, BadgeVariant> = {
  processing: "neutral",
  balanced: "emerald",
  exception: "gold",
}

function batchStatusBadgeVariant(status: string): BadgeVariant {
  return BATCH_STATUS_BADGE[status] ?? "neutral"
}

export function BalanceImport() {
  const [pools, setPools] = useState<Pool[]>([])
  const [isLoadingPools, setIsLoadingPools] = useState(true)
  const [selectedPoolId, setSelectedPoolId] = useState("")

  const [valueDate, setValueDate] = useState("")
  const [controlTotalExpected, setControlTotalExpected] = useState("")
  const [rows, setRows] = useState<RecordRow[]>([{ participant_class: "", balance_amount: "" }])

  const [formError, setFormError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<BalanceImportResult | null>(null)

  const [history, setHistory] = useState<BalanceImportBatch[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [historyError, setHistoryError] = useState("")

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        if (data.length > 0) {
          setSelectedPoolId(data[0].id)
        }
      })
      .catch(() => setFormError("Failed to load pools"))
      .finally(() => setIsLoadingPools(false))
  }, [])

  function loadHistory(poolId: string) {
    setIsLoadingHistory(true)
    setHistoryError("")
    fetchImportHistory(poolId)
      .then(setHistory)
      .catch(() => setHistoryError("Failed to load data"))
      .finally(() => setIsLoadingHistory(false))
  }

  useEffect(() => {
    if (selectedPoolId) {
      loadHistory(selectedPoolId)
    }
  }, [selectedPoolId])

  function updateRow(index: number, field: keyof RecordRow, value: string) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
  }

  function addRow() {
    setRows((prev) => [...prev, { participant_class: "", balance_amount: "" }])
  }

  function removeRow(index: number) {
    setRows((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev))
  }

  async function handleImport(event: FormEvent) {
    event.preventDefault()
    setFormError("")
    setResult(null)
    setIsSubmitting(true)

    try {
      const importResult = await importBalances({
        pool: selectedPoolId,
        value_date: valueDate,
        control_total_expected: controlTotalExpected || null,
        records: rows,
      })
      setResult(importResult)
      loadHistory(selectedPoolId)
    } catch (err) {
      setFormError(extractErrorMessage(err, "Unable to import balances."))
    } finally {
      setIsSubmitting(false)
    }
  }

  const historyColumns: TableColumn<BalanceImportBatch>[] = [
    { header: "Value Date", accessor: (batch) => batch.value_date },
    {
      header: "Status",
      accessor: (batch) => <Badge variant={batchStatusBadgeVariant(batch.status)}>{batch.status}</Badge>,
    },
    { header: "Control Total Actual", accessor: (batch) => batch.control_total_actual ?? "—" },
  ]

  return (
    <div>
      <Card title="Import Balances" className="mb-6">
        {isLoadingPools ? (
          <div className="flex items-center gap-2 text-sm text-ink-secondary">
            <Spinner className="h-4 w-4" />
            Loading pools...
          </div>
        ) : pools.length === 0 ? (
          <p className="text-sm text-gold-400">No pools available. Create a pool first.</p>
        ) : (
          <form onSubmit={handleImport} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                  Pool
                </label>
                <select
                  value={selectedPoolId}
                  onChange={(e) => setSelectedPoolId(e.target.value)}
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                >
                  {pools.map((pool) => (
                    <option key={pool.id} value={pool.id}>
                      {pool.name} ({pool.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                  Value Date
                </label>
                <input
                  type="date"
                  value={valueDate}
                  onChange={(e) => setValueDate(e.target.value)}
                  required
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                  Control Total Expected
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={controlTotalExpected}
                  onChange={(e) => setControlTotalExpected(e.target.value)}
                  placeholder="Optional"
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                Records
              </p>
              <div className="space-y-2">
                {rows.map((row, index) => (
                  <div key={index} className="flex gap-2">
                    <input
                      type="text"
                      value={row.participant_class}
                      onChange={(e) => updateRow(index, "participant_class", e.target.value)}
                      placeholder="Participant class"
                      required
                      className="flex-1 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                    />
                    <input
                      type="number"
                      step="0.01"
                      value={row.balance_amount}
                      onChange={(e) => updateRow(index, "balance_amount", e.target.value)}
                      placeholder="Balance amount"
                      required
                      className="flex-1 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => removeRow(index)}
                      disabled={rows.length === 1}
                      className="px-2 text-sm text-red-400 hover:text-red-300 disabled:opacity-30"
                      aria-label="Remove row"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={addRow}
                className="mt-2 text-sm font-medium text-emerald-400 hover:text-emerald-300"
              >
                + Add Row
              </button>
            </div>

            {formError && <p className="text-sm text-red-400">{formError}</p>}

            <Button type="submit" variant="primary" disabled={isSubmitting}>
              {isSubmitting ? <Spinner className="h-4 w-4" /> : "Import"}
            </Button>
          </form>
        )}
      </Card>

      {result && (
        <Card title="Import Summary" className="mb-6">
          <div className="mb-3 flex flex-wrap items-center gap-4 text-sm text-ink-secondary">
            <span>Total Records: {result.total_records}</span>
            <span>Matched: {result.matched_records}</span>
            <span>Exceptions: {result.exception_count}</span>
            <Badge variant={batchStatusBadgeVariant(result.status)}>{result.status}</Badge>
          </div>
          {result.errors.length > 0 && (
            <ul className="list-inside list-disc space-y-1 text-sm text-red-400">
              {result.errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <Card title="Import History">
        {isLoadingHistory && (
          <div className="flex items-center gap-2 text-sm text-ink-secondary">
            <Spinner className="h-4 w-4" />
            Loading...
          </div>
        )}
        {historyError && <p className="text-sm text-red-400">{historyError}</p>}
        {!isLoadingHistory && !historyError && (
          history.length === 0 ? (
            <p className="text-sm text-ink-secondary">No import history yet.</p>
          ) : (
            <Table columns={historyColumns} data={history} keyField={(batch) => batch.id} />
          )
        )}
      </Card>
    </div>
  )
}
