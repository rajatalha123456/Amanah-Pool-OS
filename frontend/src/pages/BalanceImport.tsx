import { useEffect, useState, type FormEvent } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { fetchPools } from "../api/pools"
import { fetchImportHistory, importBalances } from "../api/balances"
import { extractErrorMessage } from "../api/errors"
import { CbsSftpDaemonPanel } from "../components/banking/CbsSftpDaemonPanel"
import type { BadgeVariant, BalanceImportBatch, BalanceImportResult, Pool } from "../types"

interface RecordRow {
  account_number: string
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

  const [valueDate, setValueDate] = useState(new Date().toISOString().split("T")[0])
  const [controlTotalExpected, setControlTotalExpected] = useState("")
  const [ingestionMode, setIngestionMode] = useState<"cbs_sftp" | "manual">("cbs_sftp")
  const [rows, setRows] = useState<RecordRow[]>([{ account_number: "", participant_class: "", balance_amount: "" }])

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
      .catch(() => setHistoryError("Failed to load import history"))
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
    setRows((prev) => [...prev, { account_number: "", participant_class: "", balance_amount: "" }])
  }

  function removeRow(index: number) {
    setRows((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev))
  }

  function fillSampleTiers() {
    const samples: RecordRow[] = [
      { account_number: "", participant_class: "Retail Mudarabah (Tier 1 - 30D)", balance_amount: "15000000.00" },
      { account_number: "", participant_class: "Corporate Term Deposit (1-Year)", balance_amount: "45000000.00" },
      { account_number: "", participant_class: "HNW Wakalah Special Investment", balance_amount: "75000000.00" },
      { account_number: "", participant_class: "Financial Institutions Placement", balance_amount: "120000000.00" },
    ]
    setRows(samples)
    const sum = samples.reduce((acc, r) => acc + Number(r.balance_amount), 0)
    setControlTotalExpected(sum.toFixed(2))
  }

  const currentRecordsTotal = rows.reduce((sum, r) => sum + (Number(r.balance_amount) || 0), 0)

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
        // Pools with participant accounts import per account number; the class
        // is then taken from the participant, so only one of the two is sent.
        records: rows
          .filter((r) => (r.account_number.trim() || r.participant_class.trim()) && r.balance_amount.trim())
          .map((r) =>
            r.account_number.trim()
              ? { account_number: r.account_number.trim(), balance_amount: r.balance_amount }
              : { participant_class: r.participant_class.trim(), balance_amount: r.balance_amount },
          ),
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
      accessor: (batch) => <Badge variant={batchStatusBadgeVariant(batch.status)}>{batch.status.toUpperCase()}</Badge>,
    },
    {
      header: "Control Total Expected",
      accessor: (batch) =>
        batch.control_total_expected
          ? `PKR ${Number(batch.control_total_expected).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
          : "—",
    },
    {
      header: "Control Total Actual",
      accessor: (batch) =>
        batch.control_total_actual
          ? `PKR ${Number(batch.control_total_actual).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
          : "—",
    },
  ]

  return (
    <div className="space-y-6">
      {/* Mode Selector */}
      <div className="flex border-b border-ink/10 gap-2">
        <button
          type="button"
          onClick={() => setIngestionMode("cbs_sftp")}
          className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors flex items-center gap-2 ${
            ingestionMode === "cbs_sftp"
              ? "bg-surface-subtle text-emerald-400 border-b-2 border-emerald-500"
              : "text-ink-secondary hover:text-ink"
          }`}
        >
          <span>⚡ Automated CBS EOD SFTP Daemon</span>
          <Badge variant="emerald">Enterprise</Badge>
        </button>
        <button
          type="button"
          onClick={() => setIngestionMode("manual")}
          className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors flex items-center gap-2 ${
            ingestionMode === "manual"
              ? "bg-surface-subtle text-emerald-400 border-b-2 border-emerald-500"
              : "text-ink-secondary hover:text-ink"
          }`}
        >
          <span>✍️ Manual Deposit Tier Entry</span>
        </button>
      </div>

      {ingestionMode === "cbs_sftp" ? (
        <CbsSftpDaemonPanel
          pools={pools}
          selectedPoolId={selectedPoolId}
          onPoolChange={setSelectedPoolId}
          valueDate={valueDate}
          onValueDateChange={setValueDate}
          onBatchCreated={() => selectedPoolId && loadHistory(selectedPoolId)}
        />
      ) : (
        <Card
          title="Balance Ingestion & Control Total Validation"
          actions={
            <Button variant="secondary" className="text-xs" onClick={fillSampleTiers}>
              + Fill Standard Deposit Tiers
            </Button>
          }
        >
          {isLoadingPools ? (
            <div className="flex items-center gap-2 py-4 text-sm text-ink-secondary">
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
                    Target Pool *
                  </label>
                  <select
                    value={selectedPoolId}
                    onChange={(e) => setSelectedPoolId(e.target.value)}
                    className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                  >
                    {pools.map((pool) => (
                      <option key={pool.id} value={pool.id}>
                        {pool.code} — {pool.name}
                      </option>
                    ))}
                  </select>
                </div>

              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                  Value Date *
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
                  Expected Control Total (PKR)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={controlTotalExpected}
                  onChange={(e) => setControlTotalExpected(e.target.value)}
                  placeholder="Optional validation total"
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                  Participant Balances & Tiers
                </p>
                <span className="text-xs text-ink-secondary">
                  Sum:{" "}
                  <strong className="text-emerald-400">
                    PKR {currentRecordsTotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </strong>
                </span>
              </div>
              <div className="space-y-2">
                {rows.map((row, index) => (
                  <div key={index} className="flex gap-2">
                    <input
                      type="text"
                      value={row.account_number}
                      onChange={(e) => updateRow(index, "account_number", e.target.value)}
                      placeholder="Account no. (e.g. AMN-GEN-0001)"
                      className="w-44 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      value={row.participant_class}
                      onChange={(e) => updateRow(index, "participant_class", e.target.value)}
                      placeholder="Class / tier (only for pools without accounts)"
                      required={!row.account_number.trim()}
                      disabled={Boolean(row.account_number.trim())}
                      className="flex-1 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none disabled:opacity-50"
                    />
                    <input
                      type="number"
                      step="0.01"
                      value={row.balance_amount}
                      onChange={(e) => updateRow(index, "balance_amount", e.target.value)}
                      placeholder="Balance amount (PKR)"
                      required
                      className="w-48 sm:w-64 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
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
              <div className="mt-3 flex items-center justify-between">
                <button
                  type="button"
                  onClick={addRow}
                  className="text-sm font-medium text-emerald-400 hover:text-emerald-300"
                >
                  + Add Another Class / Tier
                </button>
              </div>
            </div>

            {formError && (
              <div className="rounded border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-400">
                {formError}
              </div>
            )}

            <div className="pt-2">
              <Button type="submit" variant="primary" disabled={isSubmitting}>
                {isSubmitting ? <Spinner className="h-4 w-4" /> : "Ingest & Validate Balances"}
              </Button>
            </div>
          </form>
        )}
      </Card>
      )}

      {result && (
        <Card title="Ingestion & Control Total Result">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4 mb-4">
            <StatCard label="Total Ingested" value={String(result.total_records)} deltaTone="neutral" />
            <StatCard label="Matched Records" value={String(result.matched_records)} deltaTone="positive" />
            <StatCard label="Exceptions" value={String(result.exception_count)} deltaTone={result.exception_count > 0 ? "negative" : "positive"} />
            <StatCard label="Batch Status" value={result.status.toUpperCase()} deltaTone={result.status === "balanced" ? "positive" : "neutral"} />
          </div>
          {result.errors.length > 0 && (
            <div className="rounded border border-amber-500/30 bg-amber-950/20 p-3 text-sm text-amber-300">
              <p className="font-semibold mb-1">Warnings / Notes:</p>
              <ul className="list-inside list-disc space-y-1">
                {result.errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      <Card title="Batch Ingestion History">
        {isLoadingHistory && (
          <div className="flex items-center gap-2 py-4 text-sm text-ink-secondary">
            <Spinner className="h-4 w-4" />
            Loading batch history...
          </div>
        )}
        {historyError && <p className="text-sm text-red-400">{historyError}</p>}
        {!isLoadingHistory && !historyError && (
          history.length === 0 ? (
            <p className="text-sm text-ink-secondary py-4">No balance imports recorded for this pool yet.</p>
          ) : (
            <Table columns={historyColumns} data={history} keyField={(batch) => batch.id} />
          )
        )}
      </Card>
    </div>
  )
}
