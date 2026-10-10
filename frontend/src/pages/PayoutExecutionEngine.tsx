import { useEffect, useState } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { Modal } from "../components/Modal"
import {
  fetchPayoutBatches,
  fetchPayoutBatchDetail,
  verifyPayoutGates,
  authorizePayoutBatch,
  dispatchPayoutSimulation,
  postPayoutContraGL,
  downloadPacs008Xml,
  type PayoutBatchDetail,
  type PayoutBatchSummary,
} from "../api/payoutClearing"
import { extractErrorMessage } from "../api/errors"

export function PayoutExecutionEngine() {
  const [batches, setBatches] = useState<PayoutBatchSummary[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string>("")
  const [batchDetail, setBatchDetail] = useState<PayoutBatchDetail | null>(null)
  const [isLoadingBatches, setIsLoadingBatches] = useState(true)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [isAuthorizing, setIsAuthorizing] = useState(false)
  const [isSimulating, setIsSimulating] = useState(false)
  const [isPostingGL, setIsPostingGL] = useState(false)
  const [injectEdgeCase, setInjectEdgeCase] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Simulation animation state
  const [simProgress, setSimProgress] = useState(0)

  // ISO XML Inspector Modal
  const [showXmlModal, setShowXmlModal] = useState(false)
  const [xmlContent, setXmlContent] = useState<string>("")
  const [isLoadingXml, setIsLoadingXml] = useState(false)
  const [copiedXml, setCopiedXml] = useState(false)

  // Filter state for transactions table
  const [channelFilter, setChannelFilter] = useState<string>("ALL")
  const [statusFilter, setStatusFilter] = useState<string>("ALL")
  const [searchQuery, setSearchQuery] = useState("")

  // Initial load
  useEffect(() => {
    async function loadBatches() {
      setIsLoadingBatches(true)
      try {
        const res = await fetchPayoutBatches()
        setBatches(res.batches)
        if (res.batches.length > 0) {
          setSelectedRunId(res.batches[0].allocation_run_id)
        }
      } catch (err) {
        setErrorMsg(extractErrorMessage(err))
      } finally {
        setIsLoadingBatches(false)
      }
    }
    loadBatches()
  }, [])

  // Load batch detail when selectedRunId changes
  useEffect(() => {
    if (!selectedRunId) return
    async function loadDetail() {
      setIsLoadingDetail(true)
      setErrorMsg(null)
      try {
        const detail = await fetchPayoutBatchDetail(selectedRunId)
        setBatchDetail(detail)
      } catch (err) {
        setErrorMsg(extractErrorMessage(err))
      } finally {
        setIsLoadingDetail(false)
      }
    }
    loadDetail()
  }, [selectedRunId])

  const handleVerifyGates = async () => {
    if (!selectedRunId) return
    setIsVerifying(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const updated = await verifyPayoutGates(selectedRunId)
      setBatchDetail(updated)
      setSuccessMsg("Pre-disbursement statutory gates verified successfully against SBP clearing regulations.")
    } catch (err) {
      setErrorMsg(extractErrorMessage(err))
    } finally {
      setIsVerifying(false)
    }
  }

  const handleAuthorizeBatch = async () => {
    if (!selectedRunId) return
    setIsAuthorizing(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const updated = await authorizePayoutBatch(selectedRunId)
      setBatchDetail(updated)
      setSuccessMsg("Disbursement batch authorized by Finance Checker. Ready for network dispatch.")
    } catch (err) {
      setErrorMsg(extractErrorMessage(err))
    } finally {
      setIsAuthorizing(false)
    }
  }

  const handleExecuteSimulation = async () => {
    if (!selectedRunId) return
    setIsSimulating(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    setSimProgress(15)

    const timer1 = setTimeout(() => setSimProgress(45), 300)
    const timer2 = setTimeout(() => setSimProgress(80), 700)

    try {
      const updated = await dispatchPayoutSimulation(selectedRunId, injectEdgeCase)
      setSimProgress(100)
      setTimeout(() => {
        setBatchDetail(updated)
        setIsSimulating(false)
        setSimProgress(0)
        setSuccessMsg(
          updated.status === "partially_settled"
            ? `Clearing completed with 1 exception: ${updated.settled_records}/${updated.total_records} settled. 1 item routed to Dormant Account suspense liability.`
            : `Clearing executed successfully! 100% (${updated.settled_records}/${updated.total_records}) settled instantly across SBP Raast and 1LINK rails.`
        )
      }, 500)
    } catch (err) {
      clearTimeout(timer1)
      clearTimeout(timer2)
      setIsSimulating(false)
      setSimProgress(0)
      setErrorMsg(extractErrorMessage(err))
    }
  }

  const handlePostContraGL = async () => {
    if (!selectedRunId) return
    setIsPostingGL(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const updated = await postPayoutContraGL(selectedRunId)
      setBatchDetail(updated)
      setSuccessMsg(`Contra-accounting GL voucher posted in Finance Ledger: ${updated.contra_voucher_code}`)
    } catch (err) {
      setErrorMsg(extractErrorMessage(err))
    } finally {
      setIsPostingGL(false)
    }
  }

  const handleOpenXmlModal = async () => {
    if (!selectedRunId) return
    setIsLoadingXml(true)
    setShowXmlModal(true)
    setCopiedXml(false)
    try {
      const xml = await downloadPacs008Xml(selectedRunId)
      setXmlContent(xml)
    } catch (err) {
      setErrorMsg(extractErrorMessage(err))
      setShowXmlModal(false)
    } finally {
      setIsLoadingXml(false)
    }
  }

  const handleCopyXml = () => {
    navigator.clipboard.writeText(xmlContent)
    setCopiedXml(true)
    setTimeout(() => setCopiedXml(false), 2000)
  }

  const handleDownloadXmlFile = () => {
    const blob = new Blob([xmlContent], { type: "application/xml" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${batchDetail?.batch_code || "batch"}_pacs008.xml`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Filtered transactions
  const transactions = batchDetail?.transactions || []
  const filteredTransactions = transactions.filter((t) => {
    if (channelFilter !== "ALL" && t.routing_channel !== channelFilter) return false
    if (statusFilter !== "ALL" && t.status !== statusFilter) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const match =
        t.beneficiary_name.toLowerCase().includes(q) ||
        t.iban.toLowerCase().includes(q) ||
        t.bank_name.toLowerCase().includes(q) ||
        t.txn_ref.toLowerCase().includes(q)
      if (!match) return false
    }
    return true
  })

  return (
    <div className="space-y-6">
      <div role="note" className="rounded-md border border-amber-500/40 bg-amber-950/30 px-3 py-2 text-xs font-semibold text-amber-300">
        SIMULATION MODE — recipients, taxes and approvals are real, but the Raast/1LINK rails are simulated: nothing is
        transmitted to any switch and no funds move.
      </div>
      {/* Top Banner / Breadcrumb */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-default pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-wider font-semibold text-emerald-400">
              BRD Module 14 / Screen 35
            </span>
            <span className="text-text-muted">•</span>
            <span className="text-xs text-text-muted">Core-Banking Clearing Rails</span>
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight flex items-center gap-3">
            Payout Execution Engine & Clearing Rails
            <Badge variant="gold">Simulated rails</Badge>
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            End-to-end clearing file generation, pre-disbursement statutory validation gates, ISO 20022 pacs.008 XML
            transmissions, and automated contra-accounting GL posting.
          </p>
        </div>

        {/* Batch Selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-text-muted uppercase tracking-wider">
            Active Batch:
          </label>
          {isLoadingBatches ? (
            <Spinner className="w-4 h-4" />
          ) : (
            <select
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="bg-bg-subtle border border-border-default rounded-md px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-brand-emerald"
            >
              {batches.map((b) => (
                <option key={b.allocation_run_id} value={b.allocation_run_id}>
                  {b.pool_code} - {b.period_month} ({b.status.toUpperCase()})
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-sm text-red-400 flex items-start justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-red-300 ml-4">
            ✕
          </button>
        </div>
      )}
      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 text-sm text-emerald-400 flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span>✅</span>
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-300 ml-4">
            ✕
          </button>
        </div>
      )}

      {isLoadingDetail ? (
        <div className="p-16 flex flex-col items-center justify-center gap-4">
          <Spinner className="w-8 h-8" />
          <p className="text-sm text-text-muted">Loading clearing batch & depositor ledger lines...</p>
        </div>
      ) : !batchDetail ? (
        <Card className="p-8 text-center text-text-muted">
          No active allocation run ready for payout clearing. Complete an allocation run or period close first.
        </Card>
      ) : (
        <>
          {/* KPI Summary Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="p-4 bg-bg-surface border-border-default">
              <span className="text-xs uppercase font-medium text-text-muted tracking-wider">
                Total Gross Profit
              </span>
              <div className="text-2xl font-bold text-text-primary mt-1">
                PKR {batchDetail.total_gross_profit.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-text-muted mt-1">
                {batchDetail.total_records} Total Beneficiaries
              </div>
            </Card>

            <Card className="p-4 bg-bg-surface border-border-default">
              <span className="text-xs uppercase font-medium text-text-muted tracking-wider">
                FBR Statutory WHT Withheld
              </span>
              <div className="text-2xl font-bold text-amber-400 mt-1">
                PKR {batchDetail.total_wht_deducted.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-text-muted mt-1">
                Active Taxpayer List (15% Filer / 30% Non-Filer)
              </div>
            </Card>

            <Card className="p-4 bg-bg-surface border-border-default">
              <span className="text-xs uppercase font-medium text-text-muted tracking-wider">
                Net Clearing Disbursable
              </span>
              <div className="text-2xl font-bold text-emerald-400 mt-1">
                PKR {batchDetail.total_net_disbursed.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-text-muted mt-1">
                SBP Raast / 1LINK Net Settlement Amount
              </div>
            </Card>

            <Card className="p-4 bg-bg-surface border-border-default flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase font-medium text-text-muted tracking-wider">
                  Clearing Batch Status
                </span>
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      batchDetail.status === "settled"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : batchDetail.status === "partially_settled"
                        ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                        : batchDetail.status === "dispatched"
                        ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                        : batchDetail.status === "authorized"
                        ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                        : "bg-slate-500/20 text-slate-300 border border-slate-500/30"
                    }`}
                  >
                    {batchDetail.status.toUpperCase()}
                  </span>
                  {batchDetail.contra_voucher_code && (
                    <Badge variant="gold">GL Posted</Badge>
                  )}
                </div>
              </div>
              <div className="text-xs text-text-muted mt-2 truncate font-mono">
                {batchDetail.batch_code}
              </div>
            </Card>
          </div>

          {/* SBP Pre-Disbursement Compliance Gates */}
          <Card className="p-5 bg-bg-surface border-border-default">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-3 border-b border-border-default">
              <div>
                <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
                  🛡️ SBP Pre-Disbursement Statutory 5-Gate Checklist
                  {batchDetail.gates_verified ? (
                    <span className="text-xs px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30 font-medium">
                      All Gates Passed
                    </span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded-full border border-amber-500/30 font-medium">
                      Verification Required
                    </span>
                  )}
                </h2>
                <p className="text-xs text-text-secondary mt-0.5">
                  State Bank of Pakistan regulations mandate that profit cannot leave pool GL without Shariah Fatwa quorum,
                  MOD-97 checksum validation, and dual authorization.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleVerifyGates}
                  disabled={isVerifying || isSimulating}
                >
                  {isVerifying ? (
                    <>
                      <Spinner className="w-4 h-4" /> Verifying...
                    </>
                  ) : (
                    "Re-Run 5 Gates"
                  )}
                </Button>

                {batchDetail.status === "validated" && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleAuthorizeBatch}
                    disabled={isAuthorizing || isSimulating}
                  >
                    {isAuthorizing ? (
                      <>
                        <Spinner className="w-4 h-4" /> Authorizing...
                      </>
                    ) : (
                      "Sign-Off as Checker"
                    )}
                  </Button>
                )}

              </div>
            </div>

            {/* Gates Grid */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {batchDetail.gate_results && Object.keys(batchDetail.gate_results).length > 0 ? (
                Object.entries(batchDetail.gate_results).map(([key, gate]) => (
                  <div
                    key={key}
                    className={`p-3 rounded-lg border text-xs flex flex-col justify-between ${
                      gate.status === "PASS"
                        ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-300"
                        : gate.status === "READY"
                        ? "bg-purple-950/20 border-purple-500/30 text-purple-300"
                        : "bg-red-950/20 border-red-500/30 text-red-300"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between font-semibold mb-1">
                        <span>{gate.name}</span>
                        <span>{gate.status === "PASS" ? "✅" : gate.status === "READY" ? "⏳" : "❌"}</span>
                      </div>
                      <p className="text-[11px] text-text-muted mt-1 leading-snug">{gate.details}</p>
                    </div>
                    <div className="mt-2 text-[10px] font-mono uppercase tracking-wider text-text-muted font-bold">
                      Status: {gate.status}
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-5 p-4 text-center text-text-muted text-xs">
                  Click "Re-Run 5 Gates" to execute automated pre-disbursement verification.
                </div>
              )}
            </div>
          </Card>

          {/* Interactive Simulated Clearing Execution Console */}
          <Card className="p-5 bg-slate-900/60 border border-slate-700/60 relative overflow-hidden">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs uppercase font-bold text-emerald-400 tracking-wider">
                    Live Clearing Rail Dispatch Console
                  </span>
                </div>
                <h3 className="text-lg font-bold text-text-primary">
                  SBP Raast Instant & 1LINK 1IBFT Dispatch Simulator
                </h3>
                <p className="text-xs text-text-secondary mt-0.5">
                  Sends customer credit transfer instructions (ISO 20022 pacs.008) directly into simulated clearing switches.
                </p>
              </div>

              {/* Action Buttons & Edge-Case Toggle */}
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer bg-bg-surface px-3 py-2 rounded-md border border-border-default">
                  <input
                    type="checkbox"
                    checked={injectEdgeCase}
                    onChange={(e) => setInjectEdgeCase(e.target.checked)}
                    className="rounded border-border-default text-brand-emerald focus:ring-0"
                  />
                  <span>Inject pacs.002 NACK (Dormant Account)</span>
                </label>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleOpenXmlModal}
                  disabled={isLoadingXml}
                >
                  📄 View pacs.008 XML
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleExecuteSimulation}
                  disabled={isSimulating}
                  className="bg-emerald-600 hover:bg-emerald-500 font-semibold"
                >
                  {isSimulating ? (
                    <>
                      <Spinner className="w-4 h-4" /> Transmitting Clearing Packets...
                    </>
                  ) : batchDetail.status === "settled" || batchDetail.status === "partially_settled" ? (
                    "⚡ Re-Simulate Clearing Dispatch"
                  ) : (
                    "🚀 Transmit SBP Raast / 1LINK Batch"
                  )}
                </Button>

                {(batchDetail.status === "settled" || batchDetail.status === "partially_settled") &&
                  !batchDetail.contra_voucher_code && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handlePostContraGL}
                      disabled={isPostingGL}
                      className="border-amber-500/40 text-amber-300 hover:bg-amber-500/10 font-semibold"
                    >
                      {isPostingGL ? (
                        <>
                          <Spinner className="w-4 h-4" /> Posting Contra GL...
                        </>
                      ) : (
                        "📚 Post Contra-Accounting GL"
                      )}
                    </Button>
                  )}

              </div>
            </div>

            {/* Simulation Progress Bar */}
            {isSimulating && (
              <div className="mt-4 pt-3 border-t border-slate-700/60">
                <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                  <span>Routing payment packets through SBP Raast switch & 1LINK clearing house...</span>
                  <span className="font-mono text-emerald-400 font-bold">{simProgress}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-2 transition-all duration-300 rounded-full"
                    style={{ width: `${simProgress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Contra GL Voucher Notice if posted */}
            {batchDetail.contra_voucher_code && (
              <div className="mt-4 pt-3 border-t border-slate-700/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs bg-emerald-950/20 p-3 rounded-lg border border-emerald-500/30">
                <div className="flex items-center gap-2 text-emerald-300">
                  <span>📖</span>
                  <span>
                    Contra-Accounting Voucher Posted:{" "}
                    <strong className="font-mono">{batchDetail.contra_voucher_code}</strong>
                  </span>
                  <span className="text-text-muted">•</span>
                  <span className="text-text-muted">
                    Dr. 2101-001 (Profit Payable) | Cr. 2102-005 (WHT) | Cr. 1001-002 (SBP Clearing)
                  </span>
                </div>
                <a
                  href="/finance-ledger"
                  className="text-emerald-400 hover:underline font-semibold flex items-center gap-1"
                >
                  View in Finance Ledger →
                </a>
              </div>
            )}
          </Card>

          {/* Granular Depositor Settlement Table */}
          <Card className="p-5 bg-bg-surface border-border-default">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
              <div>
                <h3 className="text-base font-semibold text-text-primary">
                  Granular Depositor Settlement Ledger
                </h3>
                <p className="text-xs text-text-secondary mt-0.5">
                  Showing all {transactions.length} depositor accounts with IBAN verification, tax withholding rates, and
                  settlement references.
                </p>
              </div>

              {/* Filters */}
              <div className="flex flex-wrap items-center gap-3">
                <input
                  type="text"
                  placeholder="Search depositor / IBAN..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-bg-subtle border border-border-default rounded-md px-3 py-1 text-xs text-text-primary focus:outline-none focus:border-brand-emerald w-48"
                />

                <select
                  value={channelFilter}
                  onChange={(e) => setChannelFilter(e.target.value)}
                  className="bg-bg-subtle border border-border-default rounded-md px-2.5 py-1 text-xs text-text-primary focus:outline-none focus:border-brand-emerald"
                >
                  <option value="ALL">All Rails</option>
                  <option value="raast">Raast Instant</option>
                  <option value="one_link">1LINK 1IBFT</option>
                  <option value="ibt">Intra-Bank IBT</option>
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-bg-subtle border border-border-default rounded-md px-2.5 py-1 text-xs text-text-primary focus:outline-none focus:border-brand-emerald"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="SETTLED">Settled</option>
                  <option value="PENDING">Pending</option>
                  <option value="FAILED">Failed</option>
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-bg-subtle text-text-muted uppercase text-[10px] tracking-wider border-b border-border-default">
                  <tr>
                    <th className="py-2.5 px-3">Beneficiary & CNIC</th>
                    <th className="py-2.5 px-3">Bank & IBAN</th>
                    <th className="py-2.5 px-3">Participant Class</th>
                    <th className="py-2.5 px-3 text-right">Gross Profit</th>
                    <th className="py-2.5 px-3 text-right">Tax (WHT)</th>
                    <th className="py-2.5 px-3 text-right">Net Payout</th>
                    <th className="py-2.5 px-3 text-center">Rail</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                    <th className="py-2.5 px-3">Settlement Ref (RRN)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  {filteredTransactions.map((t) => (
                    <tr key={t.id} className="hover:bg-bg-subtle/50 transition-colors">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-text-primary">{t.beneficiary_name}</div>
                        <div className="text-[11px] text-text-muted font-mono">{t.cnic_ntn}</div>
                      </td>

                      <td className="py-2.5 px-3">
                        <div className="text-text-primary flex items-center gap-1.5 font-medium">
                          <span>{t.bank_name}</span>
                        </div>
                        <div className="text-[11px] font-mono text-text-muted flex items-center gap-1">
                          <span>{t.iban}</span>
                          {t.iban_valid ? (
                            <span className="text-[9px] px-1 py-0.2 bg-emerald-500/10 text-emerald-400 rounded">
                              MOD-97
                            </span>
                          ) : (
                            <span className="text-[9px] px-1 py-0.2 bg-red-500/10 text-red-400 rounded">
                              INVALID
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-2.5 px-3 text-text-muted">{t.participant_class}</td>

                      <td className="py-2.5 px-3 text-right font-medium text-text-primary font-mono">
                        PKR {t.gross_profit.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>

                      <td className="py-2.5 px-3 text-right font-mono">
                        <span className="text-amber-400 font-medium">
                          -PKR {t.wht_amount.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                        </span>
                        <div className="text-[10px] text-text-muted">
                          {t.tax_status === "filer" ? "Filer (15%)" : "Non-Filer (30%)"}
                        </div>
                      </td>

                      <td className="py-2.5 px-3 text-right font-bold text-emerald-400 font-mono">
                        PKR {t.net_payout.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${
                            t.routing_channel === "raast"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : t.routing_channel === "one_link"
                              ? "bg-blue-500/20 text-blue-300"
                              : "bg-purple-500/20 text-purple-300"
                          }`}
                        >
                          {t.routing_channel === "raast"
                            ? "Raast"
                            : t.routing_channel === "one_link"
                            ? "1LINK"
                            : "IBT"}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                            t.status === "SETTLED"
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                              : t.status === "FAILED"
                              ? "bg-red-500/20 text-red-400 border border-red-500/30"
                              : "bg-slate-500/20 text-slate-300 border border-slate-500/30"
                          }`}
                        >
                          {t.status}
                        </span>
                        {t.latency_ms && (
                          <div className="text-[9px] text-text-muted mt-0.5 font-mono">{t.latency_ms}ms</div>
                        )}
                      </td>

                      <td className="py-2.5 px-3 font-mono text-[11px]">
                        {t.clearing_rrn ? (
                          <div className="text-text-primary truncate max-w-[160px]">{t.clearing_rrn}</div>
                        ) : (
                          <span className="text-text-muted italic">Queued</span>
                        )}
                        {t.response_code && (
                          <div
                            className={`text-[10px] ${
                              t.response_code === "ACTC" ? "text-emerald-400" : "text-red-400"
                            }`}
                          >
                            Code: {t.response_code}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ISO 20022 pacs.008 XML Inspector Modal */}
      {showXmlModal && (
        <Modal
          isOpen={showXmlModal}
          onClose={() => setShowXmlModal(false)}
          title="SBP Raast ISO 20022 pacs.008.001.08 XML Feed Inspector"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-text-muted border-b border-border-default pb-2">
              <div>
                <span>Standard: </span>
                <strong className="text-text-primary font-mono">pacs.008.001.08 (FIToFICstmrCdtTrf)</strong>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={handleCopyXml}>
                  {copiedXml ? "Copied!" : "📋 Copy XML"}
                </Button>
                <Button variant="primary" size="sm" onClick={handleDownloadXmlFile}>
                  ⬇️ Download XML
                </Button>
              </div>
            </div>

            {isLoadingXml ? (
              <div className="p-12 flex justify-center">
                <Spinner className="w-6 h-6" />
              </div>
            ) : (
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 max-h-[500px] overflow-y-auto font-mono text-xs text-emerald-300">
                <pre className="whitespace-pre-wrap">{xmlContent}</pre>
              </div>
            )}

            <div className="text-xs text-text-muted">
              This ISO 20022 pacs.008 customer credit transfer feed is ready for direct submission to the State Bank of Pakistan
              Raast RTGS clearing gateway or 1LINK switch.
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
