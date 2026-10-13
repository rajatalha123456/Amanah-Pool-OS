p = "frontend/src/pages/AllocationSimulator.tsx"
s = open(p, encoding="utf-8").read()

def sub(old, new, count=1):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, count)

# default pool: an open bank pool first (a draft pool made for testing must not hide the live ones)
sub('''          const generalPool = data.find(
            (p) =>
              p.name.toLowerCase().includes("general") ||''', '''          const generalPool = data.find((p) => p.status === "open" && p.product_detail?.operating_model === "bank_pool") || data.find(
            (p) =>
              p.name.toLowerCase().includes("general") ||''')

# every role can choose the pool whose runs it wants to see
sub('''              <RoleGate roles={["pool_manager", "finance_maker"]} fallback={<p className="text-xs text-ink-secondary">Read-only for your role: runs are prepared by the Pool Manager or the Finance Maker.</p>}>''',
    '''              <RoleGate
                roles={["pool_manager", "finance_maker"]}
                fallback={
                  <div className="space-y-3">
                    <p className="text-xs text-ink-secondary">Read-only for your role: runs are prepared by the Pool Manager or the Finance Maker.</p>
                    <label className="block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                      Pool
                      <select
                        value={selectedPoolId}
                        onChange={(e) => setSelectedPoolId(e.target.value)}
                        className="mt-1.5 block w-full max-w-md rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm normal-case text-ink-primary focus:border-emerald-500 focus:outline-none"
                      >
                        {pools.map((pool) => (
                          <option key={pool.id} value={pool.id}>
                            {pool.code} — {pool.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                }
              >''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
