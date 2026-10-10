import { useEffect, useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import { Modal } from "../Modal"
import { fetchPools } from "../../api/pools"
import {
  compileEvidenceBundle,
  downloadEvidenceBundleZip,
  type EvidenceBundlePayload,
  type EvidenceArtifact,
} from "../../api/evidenceBundle"
import { extractErrorMessage } from "../../api/errors"
import type { Pool } from "../../types"

const AUDIT_MANDATES = [
  "State Bank of Pakistan Annual Comprehensive Inspection",
  "External Shariah Board Compliance Audit (AAOIFI Standard 13)",
  "Statutory Financial Year-End Audit (Big 4 Review)",
  "Internal Risk & Compliance Oversight Examination",
]

const ARTIFACT_ICONS: Record<string, string> = {
  "ART-01-FATWA": "📜",
  "ART-02-PERIOD-CLOSE": "🔒",
  "ART-03-ALLOCATION": "📊",
  "ART-04-GL-JOURNALS": "📖",
  "ART-05-RAAST-CLEARING": "⚡",
  "ART-06-CONCENTRATION-RISK": "🛡️",
  "ART-07-RECONCILIATION": "⚖️",
  "ART-08-AUDIT-MERKLE-TRAIL": "🔗",
}

export function EvidenceBundleBuilder() {
  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState<string>("")
  const [periodDate, setPeriodDate] = useState<string>("2026-09-30")
  const [auditMandate, setAuditMandate] = useState<string>(AUDIT_MANDATES[0])

  const [bundle, setBundle] = useState<EvidenceBundlePayload | null>(null)
  const [isCompiling, setIsCompiling] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [selectedArtifact, setSelectedArtifact] = useState<EvidenceArtifact | null>(null)
  const [copiedText, setCopiedText] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        if (data.length > 0) {
          setSelectedPoolId(data[0].id)
          handleCompile(data[0].id, periodDate, auditMandate)
        }
      })
      .catch((err) => setErrorMsg(extractErrorMessage(err)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCompile = async (poolId = selectedPoolId, pDate = periodDate, mandate = auditMandate) => {
    if (!poolId) return
    setIsCompiling(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const data = await compileEvidenceBundle({
        pool_id: poolId,
        period_date: pDate,
        audit_type: mandate,
      })
      setBundle(data)
      setSuccessMsg(
        `SBP Regulatory Evidence Bundle compiled and sealed! Master Checksum: ${data.master_bundle_seal.slice(0, 24)}...`
      )
    } catch (err) {
      setErrorMsg(extractErrorMessage(err))
    } finally {
      setIsCompiling(false)
    }
  }

  const handleDownload = async () => {
    if (!selectedPoolId) return
    setIsDownloading(true)
    setErrorMsg(null)
    try {
      await downloadEvidenceBundleZip({
        pool_id: selectedPoolId,
        period_date: periodDate,
        audit_type: auditMandate,
      })
      setSuccessMsg("SBP Evidence Bundle ZIP archive downloaded successfully.")
    } catch (err) {
      setErrorMsg(extractErrorMessage(err))
    } finally {
      setIsDownloading(false)
    }
  }

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedText(id)
    setTimeout(() => setCopiedText(null), 2000)
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-default pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-wider font-semibold text-emerald-400">
              BRD Screen Inventory: AI & Assurance Screen 7 / Screen 39
            </span>
            <span className="text-text-muted">•</span>
            <span className="text-xs text-text-muted">AAOIFI & SBP Inspection Dossier</span>
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight flex items-center gap-3">
            Regulatory Evidence Bundle Builder
            <Badge variant="gold">Regulator Dossier</Badge>
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Aggregates Shariah Fatwa quorum attestations, period-close Merkle seals, double-entry GL vouchers, Raast
            clearing ISO 20022 XML feeds, and concentration risk metrics into a single verifiable compliance package.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleCompile()}
            disabled={isCompiling || isDownloading}
          >
            {isCompiling ? <Spinner className="w-4 h-4" /> : "🔄 Re-Compile Bundle"}
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleDownload}
            disabled={isCompiling || isDownloading || !bundle}
            className="bg-emerald-600 hover:bg-emerald-500 font-semibold"
          >
            {isDownloading ? <Spinner className="w-4 h-4" /> : "⬇️ Download SBP ZIP Package"}
          </Button>
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
            <span>🛡️</span>
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-300 ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Scope Selector Card */}
      <Card className="p-5 bg-bg-surface border-border-default">
        <h3 className="text-sm font-bold uppercase tracking-wider text-text-muted mb-3">
          1. Configure Regulatory Audit Scope & Mandate
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase mb-1">
              Target Pool:
            </label>
            <select
              value={selectedPoolId}
              onChange={(e) => {
                setSelectedPoolId(e.target.value)
                handleCompile(e.target.value, periodDate, auditMandate)
              }}
              className="w-full bg-bg-subtle border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-emerald"
            >
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase mb-1">
              Audit Period Cutoff:
            </label>
            <input
              type="date"
              value={periodDate}
              onChange={(e) => {
                setPeriodDate(e.target.value)
                handleCompile(selectedPoolId, e.target.value, auditMandate)
              }}
              className="w-full bg-bg-subtle border border-border-default rounded-md px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-brand-emerald"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase mb-1">
              Audit Mandate / Inspection Authority:
            </label>
            <select
              value={auditMandate}
              onChange={(e) => {
                setAuditMandate(e.target.value)
                handleCompile(selectedPoolId, periodDate, e.target.value)
              }}
              className="w-full bg-bg-subtle border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-emerald"
            >
              {AUDIT_MANDATES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Master Cryptographic Seal Banner */}
      {bundle && (
        <Card className="p-6 bg-gradient-to-r from-navy-950 via-slate-900 to-emerald-950/40 border border-emerald-500/40 shadow-xl">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🏛️</span>
                <div>
                  <h3 className="text-lg font-bold text-text-primary">
                    State Bank of Pakistan Compliance Manifest
                  </h3>
                  <p className="text-xs text-emerald-400 font-mono">
                    Bundle ID: {bundle.bundle_id} • Framework: {bundle.regulatory_framework}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4 text-xs text-text-muted pt-1">
                <span>
                  Target: <strong className="text-text-primary">{bundle.pool_name}</strong>
                </span>
                <span>•</span>
                <span>
                  Period: <strong className="text-text-primary">{bundle.period_month}</strong>
                </span>
                <span>•</span>
                <span>
                  Verified Artifacts: <strong className="text-emerald-400">{bundle.artifacts_count} / 8 Included</strong>
                </span>
                <span>•</span>
                <span>
                  Auditor: <strong className="text-text-primary">{bundle.compiled_by_email}</strong>
                </span>
              </div>
            </div>

            {/* Seal Display Box */}
            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-emerald-500/30 min-w-[320px]">
              <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                <span className="font-semibold text-emerald-300 uppercase tracking-wider text-[10px]">
                  Master Cryptographic Seal (SHA-256)
                </span>
                <button
                  onClick={() => handleCopy(bundle.master_bundle_seal, "master-seal")}
                  className="text-[11px] text-brand-emerald hover:underline font-mono"
                >
                  {copiedText === "master-seal" ? "Copied!" : "Copy Seal"}
                </button>
              </div>
              <div className="font-mono text-xs text-emerald-400 font-bold truncate">
                {bundle.master_bundle_seal}
              </div>
              <div className="text-[10px] text-text-muted mt-1 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                <span>Deterministic Checksum • Tamper-Evident Subledger Verified</span>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* 8-Artifact Assembly Grid */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-wider text-text-muted">
          2. Verified Evidentiary Artifacts Matrix (8-Point SBP Verification)
        </h3>

        {isCompiling ? (
          <div className="p-16 flex flex-col items-center justify-center gap-4 bg-bg-surface rounded-xl border border-border-default">
            <Spinner className="w-8 h-8" />
            <p className="text-sm text-text-muted">Compiling cryptographic evidence bundle & Merkle proofs...</p>
          </div>
        ) : !bundle ? (
          <div className="p-12 text-center text-text-muted bg-bg-surface rounded-xl border border-border-default text-xs">
            Select pool and click "Compile Bundle".
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {bundle.artifacts.map((a) => {
              const icon = ARTIFACT_ICONS[a.meta.artifact_id] || "📄"
              return (
                <Card
                  key={a.meta.artifact_id}
                  className="p-4 bg-bg-surface border-border-default hover:border-emerald-500/40 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xl">{icon}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        CONFIRMED
                      </span>
                    </div>

                    <div className="font-mono text-[10px] text-emerald-400 font-semibold mb-0.5">
                      {a.meta.artifact_id}
                    </div>
                    <h4 className="text-xs font-bold text-text-primary line-clamp-2 leading-snug">
                      {a.meta.name}
                    </h4>

                    <div className="mt-3 text-[10px] font-mono text-text-muted truncate">
                      SHA-256: {a.hash.slice(0, 16)}...
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-border-default flex items-center justify-between">
                    <button
                      onClick={() => handleCopy(a.hash, a.meta.artifact_id)}
                      className="text-[10px] text-text-muted hover:text-text-primary font-mono"
                    >
                      {copiedText === a.meta.artifact_id ? "Copied" : "Copy Hash"}
                    </button>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setSelectedArtifact(a)}
                      className="text-[10px] py-0.5 px-2"
                    >
                      Preview Artifact
                    </Button>
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      {/* Artifact Preview Modal */}
      {selectedArtifact && (
        <Modal
          isOpen={Boolean(selectedArtifact)}
          onClose={() => setSelectedArtifact(null)}
          title={`Evidentiary Artifact Inspection - ${selectedArtifact.meta.artifact_id}`}
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-text-muted border-b border-border-default pb-2">
              <div>
                <strong className="text-text-primary text-sm">{selectedArtifact.meta.name}</strong>
              </div>
              <span className="font-mono text-emerald-400 text-xs font-bold">
                ✓ Verified SHA-256 Checksum
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono space-y-1">
              <div className="text-text-muted">Artifact Checksum:</div>
              <div className="text-emerald-400 break-all">{selectedArtifact.hash}</div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary mb-1">
                Canonical Structured Payload
              </h4>
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 max-h-[400px] overflow-y-auto font-mono text-xs text-emerald-300">
                <pre className="whitespace-pre-wrap">{JSON.stringify(selectedArtifact.meta, null, 2)}</pre>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-border-default">
              <Button variant="secondary" size="sm" onClick={() => setSelectedArtifact(null)}>
                Close Preview
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
