import { useState, type FormEvent } from "react"
import { Button } from "../Button"
import { Card } from "../Card"
import { extractErrorMessage } from "../../api/errors"
import { downloadPeriodReportCsv, fetchPeriodReport, type PeriodReport } from "../../api/periodReport"

const INPUT =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const SKIP = new Set(["pool_code", "pool_name", "operating_model", "contract_type", "status"])
const label = (key: string) => key.replace(/_/g, " ")

/** Periodic report per pool for a date range, computed from recorded data and sealed with a content hash. */
export function PeriodReportPanel() {
  const [range, setRange] = useState({ start: "", end: "" })
  const [report, setReport] = useState<PeriodReport | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function run(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError("")
    try {
      setReport(await fetchPeriodReport(range.start, range.end))
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to build the report."))
    } finally {
      setBusy(false)
    }
  }

  async function download() {
    try {
      const blob = await downloadPeriodReportCsv(range.start, range.end)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `period_report_${range.start}_${range.end}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to download the report."))
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Periodic pool report">
        <form className="flex flex-wrap items-end gap-3" onSubmit={run}>
          <label className="text-xs text-ink-secondary">
            From
            <input required type="date" className={`${INPUT} mt-1 block`} value={range.start} onChange={(e) => setRange({ ...range, start: e.target.value })} />
          </label>
          <label className="text-xs text-ink-secondary">
            To
            <input required type="date" className={`${INPUT} mt-1 block`} value={range.end} onChange={(e) => setRange({ ...range, end: e.target.value })} />
          </label>
          <Button type="submit" variant="primary" disabled={busy}>
            Build report
          </Button>
          {report && (
            <Button type="button" variant="secondary" onClick={() => void download()}>
              Download CSV
            </Button>
          )}
        </form>
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      </Card>

      {report && (
        <Card title={`${report.period_start} to ${report.period_end}`}>
          <p className="mb-3 text-xs text-ink-secondary">{report.basis}</p>
          <p className="mb-4 font-mono text-[11px] text-ink-muted">content hash {report.content_hash}</p>
          <div className="space-y-4">
            {report.pools.map((row) => (
              <div key={row.pool_code} className="rounded-lg border border-white/8 bg-navy-900/50 p-3">
                <p className="text-sm font-semibold text-ink-primary">
                  {row.pool_name} <span className="font-mono text-xs text-ink-muted">({row.pool_code})</span>{" "}
                  <span className="text-xs text-ink-secondary">
                    {row.operating_model.replace(/_/g, " ")} · {row.contract_type.replace(/_/g, " ")} · {row.status.replace(/_/g, " ")}
                  </span>
                </p>
                <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-3">
                  {Object.entries(row)
                    .filter(([key]) => !SKIP.has(key))
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between gap-2">
                        <span className="capitalize text-ink-secondary">{label(key)}</span>
                        <span className="font-mono text-ink-primary">
                          {value === null || value === undefined ? "-" : /^-?\d+\.\d+$/.test(String(value)) ? Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 }) : String(value)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
