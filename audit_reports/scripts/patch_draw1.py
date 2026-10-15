import re


def edit(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:100])
        s = s.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(s)


# ---- backend: the one-step endpoints can no longer bypass the published seal -------------------------------
edit("backend/apps/circles/views.py", [
    ('''        try:
            pool = Pool.objects.get(pk=pool_id)
        except Pool.DoesNotExist:
            raise ValidationError("Pool not found.")

        result = run_draw_for_pool(pool, user=request.user)
''', '''        try:
            pool = Pool.objects.get(pk=pool_id)
        except Pool.DoesNotExist:
            raise ValidationError("Pool not found.")

        # The seal must be published before the members' seed exists, so a one-step draw is not allowed: this endpoint
        # reveals the draw that was committed earlier (circles/draws/commit/).
        result = _reveal_committed_draw(pool, request.data.get("client_seed"), request.user)
'''),
    ('''        client_seed = request.data.get("client_seed") or "entropy-client-browser"
        force_reshuffle = request.data.get("force_reshuffle", False)
''', '''        client_seed = request.data.get("client_seed")
        force_reshuffle = request.data.get("force_reshuffle", False)
'''),
    ('''            result = run_draw_for_pool(pool, client_seed=client_seed, user=request.user)
''', '''            result = _reveal_committed_draw(pool, client_seed, request.user)
'''),
    ("from .rotation import run_draw as run_draw_for_pool\n", '''from .rotation import execute_draw as _execute_draw
from .models import CircleDraw, DrawStatus


def _reveal_committed_draw(pool, client_seed, user):
    """Reveals the draw already committed for this circle with the members' seed (commit first, then reveal)."""
    draw = CircleDraw.objects.filter(pool=pool, status=DrawStatus.COMMITTED).order_by("sequence").first()
    if draw is None:
        raise ValidationError(
            "There is no committed draw. Commit (seal) the draw first, then reveal it with the members' seed."
        )
    executed = _execute_draw(draw, client_seed, user)
    return {"seed": executed.server_seed, "assignments": executed.assignments, "draw_id": str(executed.id)}
'''),
])

# ---- backend tests: commit first, then reveal ----------------------------------------------------------------------
edit("backend/apps/circles/tests.py", [
    ('''        self.authenticate(self.pool_manager)
        draw_response = self.client.post(
            reverse("circle-member-run-draw", args=[str(self.pool.id)])
        )
        self.assertEqual(draw_response.status_code, status.HTTP_200_OK)''', '''        self.authenticate(self.pool_manager)
        # No one-step draw: revealing without a published seal is refused.
        unsealed = self.client.post(reverse("circle-member-run-draw", args=[str(self.pool.id)]), {"client_seed": "members-seed"}, format="json")
        self.assertEqual(unsealed.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("committed", str(unsealed.data))
        self.assertEqual(self.client.post("/api/v1/circles/draws/commit/", {"pool": str(self.pool.id)}, format="json").status_code, status.HTTP_201_CREATED)
        no_seed = self.client.post(reverse("circle-member-run-draw", args=[str(self.pool.id)]), {}, format="json")
        self.assertEqual(no_seed.status_code, status.HTTP_400_BAD_REQUEST)
        draw_response = self.client.post(
            reverse("circle-member-run-draw", args=[str(self.pool.id)]), {"client_seed": "members-seed"}, format="json"
        )
        self.assertEqual(draw_response.status_code, status.HTTP_200_OK, draw_response.data)'''),
])

# ---- frontend: Draw Room console is the two-step ceremony ------------------------------------------------------------
c = "frontend/src/components/circles/DrawRoomConsole.tsx"
s = open(c, encoding="utf-8").read()
a = s.index("  const [isSpinning, setIsSpinning]")
b = s.index("  const [drawResult, setDrawResult]")
s = s[:a] + '''  const [isWorking, setIsWorking] = useState(false)
  const [clientSeed, setClientSeed] = useState<string>("")
''' + s[b:]
s = s.replace('''  const [swapReason, setSwapReason] = useState<string>(
    "Urgent family medical emergency advancement",
  )''', '''  const [swapReason, setSwapReason] = useState<string>("")''', 1)
a = s.index("  async function handleExecuteDraw(")
b = s.index("  async function handleSwapSubmit(")
s = s[:a] + '''  // Step 1: seal. The server fixes its secret and publishes only its hash; nobody can change the outcome after this.
  async function handleCommit() {
    setIsWorking(true)
    setError(null)
    try {
      await commitCircleDraw(poolId)
      await loadStatus()
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Could not seal the draw"))
    } finally {
      setIsWorking(false)
    }
  }

  // Step 2: reveal. The members' own seed is added, the order is computed and the server secret is published.
  async function handleReveal() {
    const drawId = data?.provably_fair.draw_id
    if (!drawId) return
    setIsWorking(true)
    setError(null)
    try {
      const res = await executeCircleDraw(drawId, clientSeed)
      setDrawResult({
        server_seed: res.server_seed ?? "",
        provably_fair_hash: res.result_hash ?? "",
        message: "Draw revealed. Anyone can recompute the order from the two seeds (Rules, Draw & Closure > Verify).",
      })
      setClientSeed("")
      await loadStatus()
      if (onDrawExecuted) onDrawExecuted()
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Draw execution failed"))
    } finally {
      setIsWorking(false)
    }
  }

''' + s[b:]
s = s.replace("  executeProvablyFairDraw,\n", "", 1)
s = s.replace('import { extractErrorMessage }', 'import { commitCircleDraw, executeCircleDraw } from "../../api/circleGovernance"\nimport { extractErrorMessage }', 1) if "circleGovernance" not in s else s
s = s.replace("🎲 Run Provably Fair Qur'ah (Lucky Draw)", "🎲 Draw ceremony (seal, then reveal)", 1)

# modal body: replace the spinner / entropy / buttons by the two steps
a = s.index('              <span\n                  className={`text-3xl font-black uppercase tracking-wide transition-all ${')
b = s.index("              {drawResult && (")
s = s[:a] + '''              <span className="text-xl font-black tracking-wide text-emerald-400">
                  {committed ? "Sealed: waiting for the members' seed" : "Not sealed yet"}
                </span>
              </div>

''' + s[b:]
a = s.index("            {/* Entropy Inputs */}")
b = s.index("      {/* Emergency Hardship Turn Swap Modal (Rule BR-007) */}")
s = s[:a] + '''            {/* The two steps */}
            <div className="space-y-3 text-left text-xs">
              <div className="rounded border border-white/10 bg-navy-950 p-3">
                <p className="font-semibold text-ink-primary">Step 1: Seal the draw</p>
                <p className="mt-1 text-ink-secondary">
                  The server fixes a secret and shows only its fingerprint. After this nobody, including the organiser, can
                  change the result.
                </p>
                <p className="mt-2 break-all font-mono text-[10px] text-emerald-400">
                  {data.provably_fair.server_seed_hash ?? "Not sealed yet"}
                </p>
                <Button className="mt-2" size="sm" variant="secondary" onClick={() => void handleCommit()} disabled={isWorking || committed}>
                  {committed ? "Sealed" : isWorking ? <Spinner className="h-4 w-4" /> : "Seal the draw"}
                </Button>
              </div>

              <div className={`rounded border border-white/10 bg-navy-950 p-3 ${committed ? "" : "opacity-50"}`}>
                <p className="font-semibold text-ink-primary">Step 2: Reveal with the members' seed</p>
                <label className="mt-1 block text-ink-secondary" htmlFor="draw-client-seed">
                  Seed chosen by the members (at least 4 characters, for example words they all agree on):
                </label>
                <input
                  id="draw-client-seed"
                  type="text"
                  value={clientSeed}
                  onChange={(e) => setClientSeed(e.target.value)}
                  disabled={!committed}
                  className="mt-1 w-full rounded border border-white/10 bg-navy-900 px-3 py-1.5 font-mono text-ink-primary focus:border-gold-500"
                />
                <Button
                  className="mt-2"
                  size="sm"
                  variant="primary"
                  onClick={() => void handleReveal()}
                  disabled={isWorking || !committed || clientSeed.trim().length < 4}
                >
                  {isWorking ? <Spinner className="h-4 w-4" /> : "Reveal the draw"}
                </Button>
              </div>
              {error && <p className="text-red-400">{error}</p>}
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-white/8 pt-4">
              <Button variant="secondary" onClick={() => setIsCeremonyOpen(false)} disabled={isWorking}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

''' + s[b:]
s = s.replace("  const eligibleForSwap =", '  const committed = data.provably_fair.draw_status === "committed"\n  const eligibleForSwap =', 1)
s = s.replace('placeholder="e.g. Hospital admission expenses, school term deadline..."', 'placeholder="The reason the two members gave (written down in their own words)"', 1)
open(c, "w", encoding="utf-8").write(s)
print("console ok")

edit("frontend/src/api/circleGovernance.ts", [
    ('export async function executeCircleDraw(drawId: string, clientSeed: string): Promise<CircleDrawRecord> {\n  return (await apiClient.post<CircleDrawRecord>(',
     'export async function executeCircleDraw(\n  drawId: string,\n  clientSeed: string,\n): Promise<CircleDrawRecord & { server_seed?: string; result_hash?: string }> {\n  return (await apiClient.post<CircleDrawRecord & { server_seed?: string; result_hash?: string }>('),
])

# ---- frontend: the circle setup tab uses the same two-step -----------------------------------------------------------
p = "frontend/src/pages/CommunityCircles.tsx"
s = open(p, encoding="utf-8").read()
a = s.index("  async function handleRunDraw() {")
b = s.index("  async function handleRecordContribution(")
s = s[:a] + '''  // The draw is a two-step ceremony (seal, then reveal with the members' seed); the Draw Room runs it.
  async function handleRunDraw() {
    setIsDrawConfirmOpen(false)
    navigate("/draw-room")
  }

''' + s[b:]
s = s.replace("  runDraw,\n", "", 1)
a = s.index("            <p className=\"text-sm text-ink-primary\">\n              This action will randomly assign")
b = s.index("            {actionError && <p className=\"text-sm text-red-400\">{actionError}</p>}", a)
s = s[:a] + '''            <p className="text-sm text-ink-primary">
              The payout order is fixed by a two-step ceremony in the Draw Room: first the draw is sealed (its fingerprint is
              published), then it is revealed with a seed the members choose. Nobody can change the result in between.
            </p>
''' + s[b:]
s = s.replace('{isSaving ? <Spinner className="h-4 w-4" /> : "Confirm Draw"}', 'Open the Draw Room', 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
