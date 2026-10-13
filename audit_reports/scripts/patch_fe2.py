ROOT = "frontend/src/"

def edit(path, pairs):
    s = open(ROOT + path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:80])
        s = s.replace(old, new, 1)
    open(ROOT + path, "w", encoding="utf-8").write(s)

edit("types/index.ts", [
    ('  status: "simulated" | "pending_approval" | "signed" | "rejected" | "reversed"',
     '  status: "simulated" | "pending_approval" | "checked" | "shariah_review" | "signed" | "rejected" | "reversed"'),
])
edit("api/investments.ts", [
    ("export async function approveDistributionRun(", '''export async function checkDistributionRun(id: string): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>(`investments/distribution-runs/${id}/check/`)
  return response.data
}

export async function shariahSignOffDistributionRun(id: string, note: string): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>(`investments/distribution-runs/${id}/shariah-sign-off/`, { note })
  return response.data
}

/** Final release by the authorized signatory (after the independent check and the Shariah review). */
export async function approveDistributionRun('''),
])
edit("components/investments/ProfitDistribution.tsx", [
    ("  approveDistributionRun,\n", "  approveDistributionRun,\n  checkDistributionRun,\n  shariahSignOffDistributionRun,\n"),
    (' * Maker drafts, an independent checker approves; signed runs are corrected by restatement.',
     ' * Maker drafts; an independent finance checker checks; the Shariah Secretariat or Board reviews; the authorized\n * signatory releases (three different people). Signed runs are corrected by restatement.'),
    ('  const canDecide = role === "finance_checker"\n',
     '  const canCheck = role === "finance_checker"\n  const canShariah = role === "shariah_secretariat" || role === "shariah_board"\n  const canRelease = role === "authorized_signatory"\n  const canReject = canCheck || canShariah || canRelease\n'),
    ('''                    {canDecide && run.status === "pending_approval" && (
                      <>
                        <Button size="sm" variant="primary" disabled={busy} onClick={() => void act(() => approveDistributionRun(run.id))}>
                          Approve
                        </Button>
                        <Button''', '''                    {canCheck && run.status === "pending_approval" && (
                      <Button size="sm" variant="primary" disabled={busy} onClick={() => void act(() => checkDistributionRun(run.id))}>
                        Independent check
                      </Button>
                    )}
                    {canShariah && run.status === "checked" && (
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={busy}
                        onClick={() => {
                          const note = window.prompt("Shariah review note (what was reviewed)") ?? ""
                          void act(() => shariahSignOffDistributionRun(run.id, note))
                        }}
                      >
                        Shariah review
                      </Button>
                    )}
                    {canRelease && run.status === "shariah_review" && (
                      <Button size="sm" variant="primary" disabled={busy} onClick={() => void act(() => approveDistributionRun(run.id))}>
                        Release
                      </Button>
                    )}
                    {canReject && ["pending_approval", "checked", "shariah_review"].includes(run.status) && (
                      <>
                        <Button'''),
])
print("ok")
