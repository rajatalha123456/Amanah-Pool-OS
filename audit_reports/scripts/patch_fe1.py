ROOT = "frontend/src/"


def edit(path, pairs):
    s = open(ROOT + path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:80])
        s = s.replace(old, new, 1)
    open(ROOT + path, "w", encoding="utf-8").write(s)


# ---- API types ------------------------------------------------------------------------------------
edit("api/governanceConfig.ts", [
    ('  kind: "approval_matrix" | "account_mapping"\n', '  kind: "approval_matrix" | "account_mapping" | "reserve_policy" | "rule_pack"\n'),
    ("  payload: Record<string, string | null>\n  before: Record<string, string | null>\n",
     "  payload: Record<string, unknown>\n  before: Record<string, unknown>\n"),
])

edit("types/index.ts", [
    ("""  reserve_type: 'per' | 'irr'
  regulatory_ceiling_pct: string
  board_approved_target_pct: string
  current_balance: string
  effective_from: string
  effective_to: string | null
  is_active: boolean""", """  reserve_type: 'per' | 'irr'
  /** % of profit (PER) or of the investors' share (IRR) appropriated each run */
  rate_percentage: string
  /** maximum reserve balance as a % of pool funds */
  cap_percentage: string
  /** system-controlled: moves only with signed runs */
  current_balance: string
  is_active: boolean"""),
])

edit("api/reservePolicies.ts", [
    ("""export async function createReservePolicy(
  data: Partial<ReservePolicy>,
): Promise<ReservePolicy> {
  const response = await apiClient.post<ReservePolicy>("allocation/reserve-policies/", data)
  return response.data
}

export async function updateReservePolicy(
  id: string,
  data: Partial<ReservePolicy>,
): Promise<ReservePolicy> {
  const response = await apiClient.patch<ReservePolicy>(`allocation/reserve-policies/${id}/`, data)
  return response.data
}""", """/** A reserve change is only PROPOSED (HTTP 202); a different finance checker approves it in Governance Config. */
export async function createReservePolicy(
  data: Partial<ReservePolicy> & { change_reason: string },
): Promise<void> {
  await apiClient.post("allocation/reserve-policies/", data)
}

export async function updateReservePolicy(
  id: string,
  data: Partial<ReservePolicy> & { change_reason: string },
): Promise<void> {
  await apiClient.patch(`allocation/reserve-policies/${id}/`, data)
}"""),
])

edit("api/jurisdiction.ts", [
    ("""export async function createJurisdictionRulePack(
  data: Partial<JurisdictionRulePack>,
): Promise<JurisdictionRulePack> {
  const response = await apiClient.post<JurisdictionRulePack>("products/jurisdiction-rule-packs/", data)
  return response.data
}

export async function updateJurisdictionRulePack(
  id: string,
  data: Partial<JurisdictionRulePack>,
): Promise<JurisdictionRulePack> {
  const response = await apiClient.patch<JurisdictionRulePack>(
    `products/jurisdiction-rule-packs/${id}/`,
    data,
  )
  return response.data
}""", """/** A rule pack change is only PROPOSED (HTTP 202); a different finance checker or the authorized signatory approves it. */
export async function createJurisdictionRulePack(
  data: Partial<JurisdictionRulePack> & { change_reason: string },
): Promise<void> {
  await apiClient.post("products/jurisdiction-rule-packs/", data)
}

export async function updateJurisdictionRulePack(
  id: string,
  data: Partial<JurisdictionRulePack> & { change_reason: string },
): Promise<void> {
  await apiClient.patch(`products/jurisdiction-rule-packs/${id}/`, data)
}"""),
])

# ---- Governance config: queue labels and who may decide ----------------------------------------------
edit("pages/GovernanceConfig.tsx", [
    ('  const canDecide = role === "finance_checker" || role === "platform_super_admin"\n',
     '  const canDecide = role === "finance_checker" || role === "authorized_signatory"\n'),
    ('{c.kind === "approval_matrix" ? "Approval matrix" : "Account mapping"} · {c.operation} · by{" "}',
     '{KIND_LABEL[c.kind] ?? c.kind} · {c.operation} · by{" "}'),
    ("Matrix and mapping edits are proposals. A different finance checker must approve them before they take effect.",
     "Matrix, mapping, reserve policy and rule pack edits are proposals. A different person (a finance checker; for a rule pack also the authorized signatory) must approve them before they take effect."),
    ('                    {Object.entries(c.payload)\n                      .map(([k, v]) => `${k}: ${c.before[k] !== undefined ? `${c.before[k]} → ` : ""}${v}`)',
     '                    {Object.entries(c.payload)\n                      .map(([k, v]) => `${k}: ${c.before[k] !== undefined ? `${show(c.before[k])} → ` : ""}${show(v)}`)'),
    ("export function GovernanceConfig() {",
     'const KIND_LABEL: Record<string, string> = {\n  approval_matrix: "Approval matrix",\n  account_mapping: "Account mapping",\n  reserve_policy: "Reserve policy (PER / IRR)",\n  rule_pack: "Jurisdiction rule pack",\n}\n\nfunction show(value: unknown): string {\n  return value !== null && typeof value === "object" ? JSON.stringify(value) : String(value)\n}\n\nexport function GovernanceConfig() {'),
])

# ---- Rule pack / reserve screen ---------------------------------------------------------------------
edit("pages/administration/JurisdictionRulePacks.tsx", [
    ("  const [actionLoading, setActionLoading] = useState(false)\n",
     '  const [actionLoading, setActionLoading] = useState(false)\n  const [notice, setNotice] = useState<string | null>(null)\n'),
    ('  const [regulatoryCeiling, setRegulatoryCeiling] = useState("2.00")\n  const [boardTarget, setBoardTarget] = useState("1.50")\n  const [policyEffectiveFrom, setPolicyEffectiveFrom] = useState("2026-01-01")\n',
     '  const [policyRate, setPolicyRate] = useState("2.00")\n  const [policyCap, setPolicyCap] = useState("5.00")\n  const [policyReason, setPolicyReason] = useState("")\n  const [packReason, setPackReason] = useState("")\n'),
    ("        rules_config: config,\n        is_active: true,\n      })\n      setShowNewPackModal(false)",
     '        rules_config: config,\n        is_active: true,\n        change_reason: packReason,\n      })\n      setNotice("Rule pack proposed. It takes effect only after a different finance checker or the authorized signatory approves it in Governance Config.")\n      setShowNewPackModal(false)'),
    ("""        reserve_type: reserveType,
        regulatory_ceiling_pct: regulatoryCeiling,
        board_approved_target_pct: boardTarget,
        effective_from: policyEffectiveFrom,
      })
      setShowPolicyModal(false)""", """        reserve_type: reserveType,
        rate_percentage: policyRate,
        cap_percentage: policyCap,
        is_active: true,
        change_reason: policyReason,
      })
      setNotice("Reserve policy proposed. A different finance checker approves it in Governance Config; the balance only moves with signed runs.")
      setShowPolicyModal(false)"""),
    ("""          <p className="font-semibold text-sm text-ink-primary">{p.pool_name || p.pool}</p>
          <span className="text-xs text-ink-secondary">{p.pool_code}</span>""",
     """          <p className="font-semibold text-sm text-ink-primary">{pools.find((x) => x.id === p.pool)?.name || p.pool}</p>
          <span className="text-xs text-ink-secondary">{pools.find((x) => x.id === p.pool)?.code}</span>"""),
    ("""    {
      header: "Regulatory Ceiling",
      accessor: (p) => `${p.regulatory_ceiling_pct}% max`,
    },
    {
      header: "Board Target",
      accessor: (p) => `${p.board_approved_target_pct}%`,
    },""", """    {
      header: "Rate",
      accessor: (p) => `${p.rate_percentage}% per run`,
    },
    {
      header: "Balance cap",
      accessor: (p) => `${p.cap_percentage}% of pool funds`,
    },"""),
    ("""    {
      header: "Effective From",
      accessor: (p) => p.effective_from,
    },
""", ""),
    ("""                <label className="block text-xs font-semibold uppercase text-ink-muted">Regulatory Ceiling % *</label>
                <input
                  type="number"
                  step="0.01"
                  value={regulatoryCeiling}
                  onChange={(e) => setRegulatoryCeiling(e.target.value)}""", """                <label className="block text-xs font-semibold uppercase text-ink-muted">Rate % per run *</label>
                <input
                  type="number"
                  step="0.01"
                  value={policyRate}
                  onChange={(e) => setPolicyRate(e.target.value)}"""),
    ("""                <label className="block text-xs font-semibold uppercase text-ink-muted">Board Approved Target % *</label>
                <input
                  type="number"
                  step="0.01"
                  value={boardTarget}
                  onChange={(e) => setBoardTarget(e.target.value)}""", """                <label className="block text-xs font-semibold uppercase text-ink-muted">Balance cap % of pool funds *</label>
                <input
                  type="number"
                  step="0.01"
                  value={policyCap}
                  onChange={(e) => setPolicyCap(e.target.value)}"""),
    ("""              <label className="block text-xs font-semibold uppercase text-ink-muted">Effective From *</label>
              <input
                type="date"
                value={policyEffectiveFrom}
                onChange={(e) => setPolicyEffectiveFrom(e.target.value)}
                required""", """              <label className="block text-xs font-semibold uppercase text-ink-muted">Reason for the change *</label>
              <input
                type="text"
                value={policyReason}
                onChange={(e) => setPolicyReason(e.target.value)}
                required"""),
    ('{actionLoading ? <Spinner className="h-4 w-4" /> : "Save Policy"}', '{actionLoading ? <Spinner className="h-4 w-4" /> : "Propose policy"}'),
    ("      {error && (", '      {notice && (\n        <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3 text-sm text-emerald-300">{notice}</div>\n      )}\n      {error && ('),
])
print("ok")
