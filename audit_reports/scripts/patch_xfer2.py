ROOT = "frontend/src/"


def edit(path, pairs):
    s = open(ROOT + path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:90])
        s = s.replace(old, new, 1)
    open(ROOT + path, "w", encoding="utf-8").write(s)


edit("api/assets.ts", [
    ('''export async function transferAsset(
  assignmentId: string,
  data: { to_pool: string; effective_date: string; reason: string },
): Promise<AssetAssignment> {
  return (await apiClient.post<AssetAssignment>(`pools/asset-assignments/${assignmentId}/transfer/`, data)).data
}''', '''export interface AssetTransferRequest {
  id: string
  asset_reference: string
  from_pool_code: string
  to_pool_code: string
  effective_date: string
  reason: string
  valuation: string
  valuation_basis: string
  status: "pending" | "approved" | "rejected"
  requested_by: number | string | null
  requested_by_name: string | null
  decided_by_name: string | null
  decision_note: string
  created_at: string
}

/** A transfer is only PROPOSED (HTTP 202): it needs a valuation and a different person's approval. */
export async function transferAsset(
  assignmentId: string,
  data: { to_pool: string; effective_date: string; reason: string; valuation: string; valuation_basis: string },
): Promise<AssetTransferRequest> {
  return (await apiClient.post<AssetTransferRequest>(`pools/asset-assignments/${assignmentId}/transfer/`, data)).data
}

export async function fetchAssetTransfers(poolId: string): Promise<AssetTransferRequest[]> {
  const response = await apiClient.get<AssetTransferRequest[]>("pools/asset-transfers/", { params: { pool: poolId } })
  return response.data
}

export async function decideAssetTransfer(id: string, verb: "approve" | "reject", reason?: string): Promise<AssetTransferRequest> {
  return (await apiClient.post<AssetTransferRequest>(`pools/asset-transfers/${id}/${verb}/`, reason ? { reason } : {})).data
}'''),
])

edit("pages/pool-detail/TransferAssetModal.tsx", [
    ('  const [reason, setReason] = useState("")\n', '  const [reason, setReason] = useState("")\n  const [valuation, setValuation] = useState("")\n  const [valuationBasis, setValuationBasis] = useState("")\n'),
    ('await transferAsset(assignmentId, { to_pool: toPool, effective_date: effectiveDate, reason })', 'await transferAsset(assignmentId, {\n        to_pool: toPool,\n        effective_date: effectiveDate,\n        reason,\n        valuation,\n        valuation_basis: valuationBasis,\n      })'),
    ("          The asset leaves this pool the day before the effective date and joins the destination pool on it.",
     "          This only proposes the transfer: a different finance checker or risk officer approves it. When approved, the asset leaves\n          this pool the day before the effective date and joins the destination pool on it, at the value stated below."),
    ('''        <div>
          <label className={LABEL}>Reason</label>''', '''        <div>
          <label className={LABEL}>Value at the transfer date (PKR)</label>
          <input required type="number" min="0.01" step="0.01" value={valuation} onChange={(e) => setValuation(e.target.value)} className={INPUT} />
        </div>
        <div>
          <label className={LABEL}>How the value was established</label>
          <input required value={valuationBasis} onChange={(e) => setValuationBasis(e.target.value)} className={INPUT} placeholder="Valuer, report number or market source" />
        </div>
        <div>
          <label className={LABEL}>Reason</label>'''),
    ('{busy ? "Transferring..." : "Transfer"}', '{busy ? "Proposing..." : "Propose transfer"}'),
])

edit("pages/pool-detail/AssignedAssetsSection.tsx", [
    ('import { fetchAssetAssignments, fetchAssets, unassignAsset } from "../../api/assets"',
     'import { useAuth } from "../../api/auth"\nimport { decideAssetTransfer, fetchAssetAssignments, fetchAssetTransfers, fetchAssets, unassignAsset, type AssetTransferRequest } from "../../api/assets"'),
    ("  const [transferId, setTransferId] = useState<string | null>(null)\n",
     '  const [transferId, setTransferId] = useState<string | null>(null)\n  const { user } = useAuth()\n  const canDecide = user?.role === "finance_checker" || user?.role === "risk_compliance"\n  const [transfers, setTransfers] = useState<AssetTransferRequest[]>([])\n  const [notice, setNotice] = useState("")\n'),
    ('''    Promise.all([fetchAssetAssignments(poolId), fetchAssets()])
      .then(([assignmentData, assetData]) => {
        setAssignments(assignmentData)''', '''    Promise.all([fetchAssetAssignments(poolId), fetchAssets(), fetchAssetTransfers(poolId)])
      .then(([assignmentData, assetData, transferData]) => {
        setAssignments(assignmentData)
        setTransfers(transferData)'''),
])
s = open(ROOT + "pages/pool-detail/AssignedAssetsSection.tsx", encoding="utf-8").read()
old = "      {actionError && <p className=\"mb-3 text-sm text-red-400\">{actionError}</p>}\n"
new = old + '''      {notice && <p className="mb-3 text-sm text-emerald-300">{notice}</p>}

      {transfers.filter((t) => t.status === "pending").length > 0 && (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-secondary">Transfers awaiting approval</p>
          {transfers
            .filter((t) => t.status === "pending")
            .map((t) => (
              <div key={t.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs">
                <p className="font-semibold text-ink-primary">
                  {t.asset_reference}: {t.from_pool_code} to {t.to_pool_code} from {t.effective_date}, valued at PKR{" "}
                  {Number(t.valuation).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
                <p className="mt-1 text-ink-secondary">
                  Basis: {t.valuation_basis} · reason: {t.reason} · proposed by {t.requested_by_name ?? "—"}
                </p>
                {canDecide && String(t.requested_by) !== String(user?.id) && (
                  <div className="mt-2 flex gap-4">
                    <button
                      type="button"
                      className="text-emerald-400"
                      onClick={() =>
                        void decideAssetTransfer(t.id, "approve")
                          .then(() => {
                            setNotice("Transfer approved and carried out.")
                            loadData()
                          })
                          .catch((err) => setActionError(extractErrorMessage(err, "Unable to approve the transfer.")))
                      }
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="text-red-400"
                      onClick={() => {
                        const reason = window.prompt("Why is the transfer refused?")
                        if (reason)
                          void decideAssetTransfer(t.id, "reject", reason)
                            .then(() => {
                              setNotice("Transfer refused.")
                              loadData()
                            })
                            .catch((err) => setActionError(extractErrorMessage(err, "Unable to refuse the transfer.")))
                      }}
                    >
                      Refuse
                    </button>
                  </div>
                )}
              </div>
            ))}
        </div>
      )}
'''
assert old in s
s = s.replace(old, new, 1)
open(ROOT + "pages/pool-detail/AssignedAssetsSection.tsx", "w", encoding="utf-8").write(s)

edit("pages/pool-detail/AssignedAssetsSection.tsx", [
    ("onTransferred={", "onTransferred={") if False else ("{transferId", "{transferId"),
]) if False else None
print("ok")
