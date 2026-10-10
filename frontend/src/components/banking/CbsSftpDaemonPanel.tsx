import { useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import {
  triggerCbsSftpDaemon,
  type CbsSftpDaemonResponse,
} from "../../api/balances"
import { extractErrorMessage } from "../../api/errors"
import type { Pool } from "../../types"

interface CbsSftpDaemonPanelProps {
  pools: Pool[]
  selectedPoolId: string
  onPoolChange: (poolId: string) => void
  valueDate: string
  onValueDateChange: (date: string) => void
  onBatchCreated?: () => void
}

export function CbsSftpDaemonPanel({
  pools,
  selectedPoolId,
  onPoolChange,
  valueDate,
  onValueDateChange,
  onBatchCreated,
}: CbsSftpDaemonPanelProps) {
  const [vendor, setVendor] = useState<string>("Temenos T24 Enterprise")
  const [scenario, setScenario] = useState<"clean" | "float_discrepancy" | "checksum_mismatch">("clean")
  const [isRunning, setIsRunning] = useState(false)
  const [daemonError, setDaemonError] = useState<string | null>(null)
  const [response, setResponse] = useState<CbsSftpDaemonResponse | null>(null)

  const handleExecute = async () => {
    if (!selectedPoolId) return
    setIsRunning(true)
    setDaemonError(null)

    try {
      const res = await triggerCbsSftpDaemon({
        pool_id: selectedPoolId,
        value_date: valueDate,
        cbs_vendor: vendor,
        scenario,
      })
      setResponse(res)
      if (res.success && onBatchCreated) {
        onBatchCreated()
      }
    } catch (err) {
      setDaemonError(extractErrorMessage(err))
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <Card
      title="⚡ Automated CBS EOD SFTP Daemon & Clearing Ingestion"
      className="border-emerald-500/20 bg-surface/80"
    >
      <div className="space-y-6">
        <p className="text-xs text-ink-secondary">
          Simulates production midnight batch extraction from the Core Banking System.
          Performs automated SSH/SFTP handshakes, SHA-256 sidecar checksum verification,
          and flags uncleared NIFT/float holds prior to daily profit accrual.
        </p>

        {/* Configuration Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-lg bg-surface-subtle border border-ink/10">
          <div>
            <label className="block text-xs font-medium text-ink-secondary mb-1">
              CBS Engine
            </label>
            <select
              value={vendor}
              onChange={(e) => setVendor(e.target.value)}
              disabled={isRunning}
              className="w-full text-xs rounded-md bg-surface border border-ink/20 px-3 py-2 text-ink"
            >
              <option value="Temenos T24 Enterprise">Temenos T24 Enterprise</option>
              <option value="Oracle Flexcube Islamic">Oracle Flexcube Islamic</option>
              <option value="Finastra Fusion Midas">Finastra Fusion Midas</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-ink-secondary mb-1">
              Target Pool
            </label>
            <select
              value={selectedPoolId}
              onChange={(e) => onPoolChange(e.target.value)}
              disabled={isRunning}
              className="w-full text-xs rounded-md bg-surface border border-ink/20 px-3 py-2 text-ink"
            >
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} - {p.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-ink-secondary mb-1">
              EOD Value Date
            </label>
            <input
              type="date"
              value={valueDate}
              onChange={(e) => onValueDateChange(e.target.value)}
              disabled={isRunning}
              className="w-full text-xs rounded-md bg-surface border border-ink/20 px-3 py-2 text-ink"
            >
            </input>
          </div>

          <div>
            <label className="block text-xs font-medium text-ink-secondary mb-1">
              Clearing Scenario
            </label>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value as any)}
              disabled={isRunning}
              className="w-full text-xs rounded-md bg-surface border border-ink/20 px-3 py-2 text-ink"
            >
              <option value="clean">✅ 100% Balanced (Zero Float)</option>
              <option value="float_discrepancy">⚠️ Float Discrepancy (PKR 1.45M Hold)</option>
              <option value="checksum_mismatch">❌ Tampered Sidecar (Checksum Error)</option>
            </select>
          </div>
        </div>

        {/* Action button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <span>Remote SFTP:</span>
            <code className="text-[11px] bg-surface-subtle px-1.5 py-0.5 rounded text-ink-secondary font-mono">
              sftp-eod.cbs.amanah-bank.internal:2222
            </code>
          </div>

          <Button
            onClick={handleExecute}
            disabled={isRunning || !selectedPoolId}
            className="flex items-center gap-2 text-xs"
          >
            {isRunning ? (
              <>
                <Spinner className="h-4 w-4" />
                <span>Polling SFTP Daemon...</span>
              </>
            ) : (
              <>
                <span>⚡ Poll Remote SFTP & Ingest Batch</span>
              </>
            )}
          </Button>
        </div>

        {/* Daemon Error Banner */}
        {daemonError && (
          <div className="p-3 rounded-lg border border-red-500/30 bg-red-950/20 text-xs text-red-300">
            <p className="font-semibold">CBS Ingestion Failure</p>
            <p className="mt-1">{daemonError}</p>
          </div>
        )}

        {/* Terminal and Live Output */}
        {response && (
          <div className="space-y-4">
            {/* Status Summary Banner */}
            <div
              className={`p-4 rounded-lg border flex flex-col md:flex-row md:items-center justify-between gap-3 ${
                response.status === "BALANCED"
                  ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-300"
                  : response.status === "EXCEPTION"
                  ? "border-gold-500/30 bg-gold-950/20 text-gold-300"
                  : "border-red-500/30 bg-red-950/20 text-red-300"
              }`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      response.status === "BALANCED"
                        ? "emerald"
                        : response.status === "EXCEPTION"
                        ? "gold"
                        : "neutral"
                    }
                  >
                    {response.status}
                  </Badge>
                  <span className="font-semibold text-xs">{response.message}</span>
                </div>
                <p className="text-[11px] mt-1 opacity-80">
                  File: {response.file_name} • Remote: {response.sftp_remote_path}
                </p>
              </div>

              {response.computed_sha256 && (
                <div className="text-right">
                  <div className="text-[10px] uppercase font-mono text-ink-muted">
                    SHA-256 Sidecar Digest
                  </div>
                  <div className="font-mono text-[11px] text-ink">
                    {response.computed_sha256.slice(0, 16)}...{response.computed_sha256.slice(-8)}
                  </div>
                </div>
              )}
            </div>

            {/* Float Discrepancy SBP Warning Callout */}
            {response.status === "EXCEPTION" && (
              <div className="p-4 rounded-lg border border-amber-500/40 bg-amber-950/30 text-xs text-amber-200 space-y-1">
                <p className="font-semibold flex items-center gap-1.5">
                  <span>🚨 SBP Float Warning:</span> Unsettled Clearing Variance Detected
                </p>
                <p className="text-[11px] text-amber-300/80">
                  Total Ledger: PKR {response.summary?.total_ledger.toLocaleString()} |
                  Uncleared Float: PKR {response.summary?.total_float.toLocaleString()} |
                  Net Available: PKR {response.summary?.total_available.toLocaleString()}.
                  An automated Exception Case has been logged into the Governance Center for Ops & Risk Sign-Off.
                </p>
              </div>
            )}

            {/* Monospace SFTP Terminal Logs */}
            <div className="rounded-lg bg-black/70 border border-ink/20 p-3 font-mono text-[11px] text-emerald-400 space-y-1 overflow-x-auto max-h-48 overflow-y-auto">
              <div className="text-ink-muted border-b border-ink/10 pb-1 mb-1 text-[10px]">
                --- SFTP DAEMON RUNTIME CONSOLE [{response.cbs_vendor}] ---
              </div>
              {response.sftp_logs.map((log, idx) => (
                <div key={idx} className="whitespace-pre-wrap">
                  {log}
                </div>
              ))}
            </div>

            {/* Ingested Accounts Breakdown Table */}
            {response.records.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-ink">
                    Ingested Core Banking Accounts ({response.records.length})
                  </h4>
                  {response.summary && (
                    <div className="text-xs text-ink-secondary">
                      Net Available:{" "}
                      <span className="font-bold text-ink">
                        PKR {response.summary.total_available.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  )}
                </div>

                <div className="overflow-x-auto rounded-lg border border-ink/10">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-surface-subtle text-ink-secondary font-medium">
                      <tr>
                        <th className="py-2 px-3">Account No</th>
                        <th className="py-2 px-3">Account Title</th>
                        <th className="py-2 px-3">Tier</th>
                        <th className="py-2 px-3 text-right">Ledger (PKR)</th>
                        <th className="py-2 px-3 text-right">Uncleared Float</th>
                        <th className="py-2 px-3 text-right">Available (PKR)</th>
                        <th className="py-2 px-3 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-ink/5">
                      {response.records.map((r, i) => (
                        <tr key={i} className="hover:bg-surface-subtle/50">
                          <td className="py-2 px-3 font-mono text-[11px] text-ink">{r.account_no}</td>
                          <td className="py-2 px-3 text-ink-secondary">{r.title}</td>
                          <td className="py-2 px-3 font-medium text-ink">{r.participant_class}</td>
                          <td className="py-2 px-3 text-right font-mono text-ink">
                            {r.ledger_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-2 px-3 text-right font-mono">
                            {r.uncleared_float > 0 ? (
                              <span className="text-gold-400 font-semibold">
                                -{r.uncleared_float.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                              </span>
                            ) : (
                              <span className="text-ink-muted">0.00</span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-right font-mono font-bold text-ink">
                            {r.available_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-2 px-3 text-center">
                            <Badge
                              variant={r.status === "SETTLED" ? "emerald" : "gold"}
                            >
                              {r.status}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
