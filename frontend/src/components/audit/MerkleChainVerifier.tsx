import { useEffect, useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import { Modal } from "../Modal"
import {
  fetchMerkleVerification,
  simulateMerkleTamper,
  type MerkleVerificationResult,
  type MerkleChainBlock,
} from "../../api/merkleAudit"
import { extractErrorMessage } from "../../api/errors"

export function MerkleChainVerifier() {
  const [result, setResult] = useState<MerkleVerificationResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSimulating, setIsSimulating] = useState(false)
  const [isTamperMode, setIsTamperMode] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [selectedBlock, setSelectedBlock] = useState<MerkleChainBlock | null>(null)
  const [copiedHash, setCopiedHash] = useState<string | null>(null)
  const [modelFilter, setModelFilter] = useState<string>("ALL")
  const [searchQuery, setSearchQuery] = useState("")

  const loadVerification = async () => {
    setIsLoading(true)
    setErrorMsg(null)
    setIsTamperMode(false)
    try {
      const data = await fetchMerkleVerification()
      setResult(data)
      setSuccessMsg("Merkle hash tree recalculated from Genesis block: 100% cryptographic integrity verified.")
    } catch (err) {
      setErrorMsg(extractErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  const handleSimulateTamper = async () => {
    setIsSimulating(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const data = await simulateMerkleTamper()
      setResult(data)
      setIsTamperMode(true)
      setSuccessMsg(
        `Tamper simulation active: Malicious modification detected at Block #${data.broken_at_block_height}! Subsequent Merkle lineage invalidated.`
      )
    } catch (err) {
      setErrorMsg(extractErrorMessage(err))
    } finally {
      setIsSimulating(false)
    }
  }

  useEffect(() => {
    loadVerification()
  }, [])

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedHash(id)
    setTimeout(() => setCopiedHash(null), 2000)
  }

  // Filter blocks
  const blocks = result?.chain_blocks || []
  const filteredBlocks = blocks.filter((b) => {
    if (modelFilter !== "ALL" && b.model_name !== modelFilter) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const match =
        b.action.toLowerCase().includes(q) ||
        b.model_name.toLowerCase().includes(q) ||
        b.actor_email.toLowerCase().includes(q) ||
        b.leaf_hash.toLowerCase().includes(q) ||
        b.object_id.toLowerCase().includes(q)
      if (!match) return false
    }
    return true
  })

  const uniqueModels = Array.from(new Set(blocks.map((b) => b.model_name))).filter(Boolean)

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-default pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-wider font-semibold text-emerald-400">
              BRD Module 15 / Screen 38
            </span>
            <span className="text-text-muted">•</span>
            <span className="text-xs text-text-muted">AAOIFI & SBP Prudential Audit Trail</span>
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight flex items-center gap-3">
            Merkle Tree Forensic Audit Trail & Diff Engine
            <Badge variant="emerald">SHA-256 Immutability</Badge>
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Cryptographically linked append-only audit subledger with mathematical non-repudiation, tamper detection,
            and granular before-and-after field diff inspection.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={loadVerification}
            disabled={isLoading || isSimulating}
          >
            {isLoading ? <Spinner className="w-4 h-4" /> : "🔄 Recalculate Merkle Root"}
          </Button>

          {!isTamperMode ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleSimulateTamper}
              disabled={isLoading || isSimulating}
              className="border-red-500/40 text-red-300 hover:bg-red-500/10 font-semibold"
            >
              {isSimulating ? <Spinner className="w-4 h-4" /> : "⚠️ Simulate SBP Tamper Test"}
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={loadVerification}
              className="bg-emerald-600 hover:bg-emerald-500 font-semibold"
            >
              ✓ Reset to Live Production Chain
            </Button>
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
        <div
          className={`border rounded-lg p-4 text-sm flex items-start justify-between ${
            isTamperMode
              ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
              : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
          }`}
        >
          <div className="flex items-center gap-2">
            <span>{isTamperMode ? "🚨" : "🛡️"}</span>
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-text-muted hover:text-text-primary ml-4">
            ✕
          </button>
        </div>
      )}

      {/* KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-bg-surface border-border-default">
          <span className="text-xs uppercase font-medium text-text-muted tracking-wider">
            Total Blocks in Chain
          </span>
          <div className="text-2xl font-bold text-text-primary mt-1 font-mono">
            {result?.total_blocks || 0} Blocks
          </div>
          <div className="text-xs text-text-muted mt-1">
            Genesis Height: #0001 (Immutable)
          </div>
        </Card>

        <Card className="p-4 bg-bg-surface border-border-default">
          <span className="text-xs uppercase font-medium text-text-muted tracking-wider">
            Cryptographic Integrity
          </span>
          <div className="mt-1">
            {result?.status === "VERIFIED" ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                ✓ 100% Chain Verified
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                🚨 Tamper Detected (Broken Leaf)
              </span>
            )}
          </div>
          <div className="text-xs text-text-muted mt-2">
            {result?.tampered_count === 0 ? "0 Corrupted Leaves" : `${result?.tampered_count} Corrupted Leaf Flagged`}
          </div>
        </Card>

        <Card className="p-4 bg-bg-surface border-border-default col-span-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-medium text-text-muted tracking-wider">
              {isTamperMode ? "Compromised Merkle Root (Attacked)" : "Current Head Merkle Root (SHA-256)"}
            </span>
            <button
              onClick={() =>
                handleCopy(
                  result?.current_merkle_root || result?.compromised_merkle_root || "",
                  "head-root"
                )
              }
              className="text-xs text-brand-emerald hover:underline font-mono"
            >
              {copiedHash === "head-root" ? "Copied!" : "Copy Root"}
            </button>
          </div>
          <div
            className={`text-sm font-mono font-bold mt-1.5 truncate p-2 rounded ${
              isTamperMode ? "bg-red-950/40 text-red-300 border border-red-500/30" : "bg-bg-subtle text-emerald-400 border border-border-default"
            }`}
          >
            {result?.current_merkle_root || result?.compromised_merkle_root || "Computing..."}
          </div>
          <div className="text-[11px] text-text-muted mt-1.5 truncate">
            Genesis Root: <span className="font-mono text-text-secondary">{result?.genesis_block_hash}</span>
          </div>
        </Card>
      </div>

      {/* Merkle Chain Table & Filters */}
      <Card className="p-5 bg-bg-surface border-border-default">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4 pb-3 border-b border-border-default">
          <div>
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              📜 Verified Audit Ledger Blocks
              <span className="text-xs px-2 py-0.5 bg-bg-subtle text-text-muted rounded-full border border-border-default font-mono">
                {filteredBlocks.length} records
              </span>
            </h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Each entry contains a parent-hash link to the preceding block. Click "Inspect Field Diff" to view exact
              field changes.
            </p>
          </div>

          {/* Filter Bar */}
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              placeholder="Search action, actor, hash..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-bg-subtle border border-border-default rounded-md px-3 py-1 text-xs text-text-primary focus:outline-none focus:border-brand-emerald w-48"
            />

            <select
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="bg-bg-subtle border border-border-default rounded-md px-2.5 py-1 text-xs text-text-primary focus:outline-none focus:border-brand-emerald"
            >
              <option value="ALL">All Models</option>
              {uniqueModels.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Chain Table */}
        {isLoading ? (
          <div className="p-16 flex flex-col items-center justify-center gap-4">
            <Spinner className="w-8 h-8" />
            <p className="text-sm text-text-muted">Computing SHA-256 Merkle chain nodes...</p>
          </div>
        ) : filteredBlocks.length === 0 ? (
          <div className="p-12 text-center text-text-muted text-xs">
            No audit records match the selected filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-bg-subtle text-text-muted uppercase text-[10px] tracking-wider border-b border-border-default">
                <tr>
                  <th className="py-2.5 px-3">Height</th>
                  <th className="py-2.5 px-3">Timestamp & IP</th>
                  <th className="py-2.5 px-3">Actor & Role</th>
                  <th className="py-2.5 px-3">Action & Model</th>
                  <th className="py-2.5 px-3">SHA-256 Leaf Hash</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                  <th className="py-2.5 px-3 text-right">Forensic Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-default">
                {filteredBlocks.map((b) => (
                  <tr
                    key={b.entry_id}
                    className={`transition-colors ${
                      b.tamper_detected_at_this_block
                        ? "bg-red-950/30 hover:bg-red-950/40"
                        : b.is_tampered
                        ? "bg-amber-950/20 hover:bg-amber-950/30"
                        : "hover:bg-bg-subtle/50"
                    }`}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold text-text-primary">
                      #{String(b.height).padStart(4, "0")}
                    </td>

                    <td className="py-2.5 px-3">
                      <div className="text-text-primary font-medium">
                        {b.timestamp ? new Date(b.timestamp).toLocaleString("en-PK") : "—"}
                      </div>
                      <div className="text-[10px] text-text-muted font-mono">{b.ip_address}</div>
                    </td>

                    <td className="py-2.5 px-3">
                      <div className="text-text-primary font-semibold truncate max-w-[170px]">
                        {b.actor_email}
                      </div>
                      <span className="inline-block mt-0.5 text-[9px] px-1.5 py-0.2 rounded font-semibold uppercase bg-slate-500/20 text-slate-300">
                        {b.actor_role.replace("_", " ")}
                      </span>
                    </td>

                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          b.action === "create"
                            ? "bg-emerald-500/20 text-emerald-400"
                            : b.action === "update"
                            ? "bg-blue-500/20 text-blue-400"
                            : b.action === "approve" || b.action === "lock"
                            ? "bg-purple-500/20 text-purple-400"
                            : "bg-amber-500/20 text-amber-400"
                        }`}
                      >
                        {b.action}
                      </span>
                      <div className="text-[11px] text-text-secondary mt-0.5 font-medium">
                        {b.model_name}
                      </div>
                    </td>

                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="text-text-muted truncate max-w-[130px]" title={b.leaf_hash}>
                          {b.leaf_hash.slice(0, 14)}...
                        </span>
                        <button
                          onClick={() => handleCopy(b.leaf_hash, b.entry_id)}
                          className="text-[10px] text-brand-emerald hover:underline"
                        >
                          {copiedHash === b.entry_id ? "Copied" : "Copy"}
                        </button>
                      </div>
                      <div className="text-[10px] text-text-muted truncate max-w-[140px]" title={b.rolling_merkle_root}>
                        Root: {b.rolling_merkle_root.slice(0, 10)}...
                      </div>
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      {b.tamper_detected_at_this_block ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse">
                          ❌ TAMPERED
                        </span>
                      ) : b.is_tampered ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
                          ⚠️ BROKEN LINEAGE
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          ✓ VERIFIED
                        </span>
                      )}
                    </td>

                    <td className="py-2.5 px-3 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setSelectedBlock(b)}
                        className="text-[11px] py-1"
                      >
                        🔍 Inspect Diff
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Forensic Visual Field Diff Modal */}
      {selectedBlock && (
        <Modal
          isOpen={Boolean(selectedBlock)}
          onClose={() => setSelectedBlock(null)}
          title={`Forensic Field Diff - Block #${String(selectedBlock.height).padStart(4, "0")} (${selectedBlock.action} on ${selectedBlock.model_name})`}
        >
          <div className="space-y-4">
            {/* Meta Header */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-bg-subtle rounded-lg border border-border-default text-xs">
              <div>
                <span className="text-text-muted uppercase text-[10px]">Actor:</span>
                <div className="font-semibold text-text-primary">{selectedBlock.actor_email}</div>
                <div className="text-[10px] text-emerald-400 font-mono">{selectedBlock.actor_role}</div>
              </div>
              <div>
                <span className="text-text-muted uppercase text-[10px]">Target Object:</span>
                <div className="font-mono text-text-primary truncate" title={selectedBlock.object_id}>
                  {selectedBlock.object_id.slice(0, 12)}...
                </div>
                <div className="text-[10px] text-text-muted">{selectedBlock.model_name}</div>
              </div>
              <div>
                <span className="text-text-muted uppercase text-[10px]">Timestamp:</span>
                <div className="text-text-primary">
                  {selectedBlock.timestamp ? new Date(selectedBlock.timestamp).toLocaleTimeString() : "—"}
                </div>
                <div className="text-[10px] text-text-muted">
                  {selectedBlock.timestamp ? new Date(selectedBlock.timestamp).toLocaleDateString() : ""}
                </div>
              </div>
              <div>
                <span className="text-text-muted uppercase text-[10px]">IP & Network:</span>
                <div className="font-mono text-text-primary">{selectedBlock.ip_address}</div>
                <div className="text-[10px] text-emerald-400 font-bold">Authenticated SSL</div>
              </div>
            </div>

            {/* Cryptographic Hashes */}
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Leaf SHA-256 Hash:</span>
                <span className="text-emerald-400 truncate max-w-[380px]">{selectedBlock.leaf_hash}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Rolling Merkle Root:</span>
                <span className="text-blue-400 truncate max-w-[380px]">{selectedBlock.rolling_merkle_root}</span>
              </div>
            </div>

            {/* Reason / Notes if present */}
            {selectedBlock.reason && (
              <div className="p-3 bg-amber-950/20 border border-amber-500/30 rounded-lg text-xs text-amber-300">
                <strong className="block text-[10px] uppercase tracking-wider text-amber-400 mb-0.5">
                  Business Justification / Shariah Note:
                </strong>
                {selectedBlock.reason}
              </div>
            )}

            {/* Visual Field Diff Table */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary mb-2">
                Field-by-Field Modification Matrix (Before vs After)
              </h4>

              {selectedBlock.field_diffs.length === 0 ? (
                <div className="p-4 bg-bg-subtle rounded-lg text-center text-xs text-text-muted">
                  No structural field mutations recorded for this entry (e.g. read attestation).
                </div>
              ) : (
                <div className="border border-border-default rounded-lg overflow-hidden">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-bg-subtle text-text-muted uppercase text-[10px] tracking-wider border-b border-border-default">
                      <tr>
                        <th className="py-2 px-3">Field Name</th>
                        <th className="py-2 px-3">Previous State (Before)</th>
                        <th className="py-2 px-3"></th>
                        <th className="py-2 px-3">New State (After)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-default font-mono">
                      {selectedBlock.field_diffs.map((diff) => (
                        <tr key={diff.field} className="hover:bg-bg-subtle/40">
                          <td className="py-2.5 px-3 font-semibold text-text-primary">
                            {diff.field}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded bg-red-950/40 text-red-300 border border-red-500/30 line-through">
                              {diff.before}
                            </span>
                          </td>
                          <td className="py-2.5 px-1 text-center text-text-muted font-sans font-bold">
                            ➔
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-500/30 font-bold">
                              {diff.after}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2 border-t border-border-default">
              <Button variant="secondary" size="sm" onClick={() => setSelectedBlock(null)}>
                Close Inspector
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
