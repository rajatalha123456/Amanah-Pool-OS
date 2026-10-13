import re

BASE = "audit_reports/"

# ---- traceability matrix: rows changed by the fixes (status, severity, note added to the evidence) ----------
updates = {
    "R-014": ("PASS", "-", "after fix F-03: AT test_super_admin_audit_log_hides_the_figures (BT governance.test_audit_fixes)"),
    "R-019": ("PASS", "-", "after fix F-04: rule pack changes are proposals (BT test_rule_pack_change_is_only_proposed_until_approved)"),
    "R-020": ("PASS", "-", "after fix F-04 (BT governance.test_audit_fixes); AT patch probe: no change persists"),
    "R-029": ("PASS", "-", "after fix F-02: pending balances refused (AT test_14, BT test_pending_balances_block_a_run)"),
    "R-040": ("PASS", "-", "after fix FIN-02: weightage > 0 in serializer and DB (AT test_16). The BRD 'maximum change' rule is still not built"),
    "R-043": ("PASS", "-", "after fix F-01: balance read-only, changes need a different checker (BT test_reserve_balance_cannot_be_set...; AT reserve test)"),
    "R-059": ("PARTIAL", "P2", "after fix F-02: pending balances block a run. A signed daily close is still not required before a run"),
    "R-060": ("PARTIAL", "P2", "after fix F-04: rule pack changes are approved and audited; the run hash still does not snapshot the pack"),
    "R-066": ("PASS", "-", "after fix F-06: 4-stage ceremony for distributions (BT DistributionCeremonyTests, 3)"),
    "R-104": ("PASS", "-", "after fix F-01/F-04: reserve and rule pack changes need approval and are audited"),
    "R-132": ("PARTIAL", "P2", "after fix F-04: pack edits are controlled, but the pack is still edited in place and not versioned"),
    "R-135": ("PASS", "-", "after fixes F-01, F-04, F-05: AT patch probe shows no uncontrolled change"),
    "R-165": ("PASS", "-", "after fix F-01/F-04"),
    "R-150": ("PARTIAL", "P2", "after fix F-07: limits come from the rule pack; defaults are labelled unconfirmed"),
    "R-041": ("PARTIAL", "P2", "after fix F-07: limits configurable; sector and obligor data are still inferred"),
}
p = BASE + "BRD_TRACEABILITY_MATRIX.md"
lines = open(p, encoding="utf-8").read().split("\n")
out = []
for line in lines:
    m = re.match(r"^\| (R-\d{3}) \|", line)
    if m and m.group(1) in updates:
        status, sev, note = updates[m.group(1)]
        cells = line.split("|")
        # table layouts differ: find the status cell (first cell starting with a status word) and the next one (severity)
        idx = next(i for i, c in enumerate(cells) if re.match(r"^\s*(PASS|PARTIAL|FAIL|MISSING|BLOCKED|NOT TESTED|NOT APPLICABLE)\b", c))
        cells[idx] = f" {status} "
        if idx + 1 < len(cells) - 1:
            cells[idx + 1] = f" {sev} "
        cells[idx - 1] = cells[idx - 1].rstrip() + f"; {note} "
        line = "|".join(cells)
    out.append(line)
text = "\n".join(out)

counts = {}
for line in text.split("\n"):
    if line.startswith("| R-"):
        for cell in line.split("|"):
            m = re.match(r"^\s*(PASS|PARTIAL|FAIL|MISSING|BLOCKED|NOT TESTED|NOT APPLICABLE)\b", cell)
            if m:
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
                break
total = sum(counts.values())
a = text.index("## Totals (R-001..R-186)")
text = text[:a] + "## Totals (R-001..R-186), after the 2026-10-13 fixes\n\n| Status | Count |\n|---|---|\n" + "\n".join(
    f"| {k} | {counts.get(k, 0)} |" for k in ("PASS", "PARTIAL", "FAIL", "MISSING", "BLOCKED", "NOT TESTED", "NOT APPLICABLE")
) + f"\n| **Total** | **{total}** |\n\nCounted by script from the rows above. Before the fixes the counts were PASS 78, PARTIAL 70, FAIL 9, MISSING 9, BLOCKED 8, NOT TESTED 10, NOT APPLICABLE 2.\nRows changed by the fixes carry an \"after fix\" note in their evidence cell. Applicable requirements: {total - counts.get('NOT APPLICABLE', 0)}.\nThe 58 screens of BRD section 15 are counted in `SCREEN_AUDIT.md`.\n"
open(p, "w", encoding="utf-8").write(text)
print(counts, total)

# ---- master report: status after fixes -----------------------------------------------------------
p = BASE + "MASTER_AUDIT_REPORT.md"
s = open(p, encoding="utf-8").read()
applicable = total - counts.get("NOT APPLICABLE", 0)
passed = counts.get("PASS", 0)
section = f"""## 0. Status after the fixes (2026-10-13, commits 8d32641, 53aaf8a)
The findings below were written before the fixes. This section records what changed. Evidence: `evidence/after_fixes/`, and the regression tests in `backend/apps/governance/test_audit_fixes.py`, `backend/apps/investments/test_distribution.py` (`DistributionCeremonyTests`).

| Finding | Status now | Evidence |
|---|---|---|
| F-01 (P0) reserve balance writable | **Fixed** | AT after: HTTP 400, balance unchanged; BT `test_reserve_balance_cannot_be_set...` |
| F-02 pending balances earn profit | **Fixed** (a signed daily close is still not required) | AT test_14 now asserts refusal; BT |
| F-03 super admin sees figures | **Fixed** | BT `test_super_admin_audit_log_hides_the_figures` |
| F-04 rule pack edited in place | **Fixed for control and audit**; version history and run-hash snapshot still open | BT; AT patch probe: no change persisted |
| F-05 account dates rewritable | **Fixed** | BT |
| F-06 distribution without Shariah stage | **Fixed** | BT `DistributionCeremonyTests` |
| F-07 hard-coded "statutory" limits | **Fixed** (limits from the rule pack; defaults labelled unconfirmed; regulator citations removed). The values themselves need Risk & counsel | code + frontend |
| F-08 no lock on distribution release | **Fixed** (no concurrent-request test yet) | code, BT `test_a_second_release...` |
| F-09 Shariah flag flips a run in progress | **Fixed** for new runs; older runs keep the live rule | BT |
| F-10 allocation page wrong pool | **Fixed** | E2E smoke 30/30 |
| F-11 open exception does not block release | **Fixed** | BT |
| F-12 Django admin | **Fixed** (off outside DEBUG) | AT |
| FIN-02 negative weightage | **Fixed** | AT test_16 |

Test results after the fixes: backend 454/454, audit tests 42/42, browser smoke 30/30 and role sweep 13/13 (one earlier fail was caused by running two Playwright jobs at once), `tsc` clean.
Requirement rows: PASS {passed} of {applicable} applicable ({round(100 * passed / applicable)}%), see the matrix.
**Readiness after the fixes: still NOT READY for real customer money**, for the reasons that are not code: no live integrations, no backup/restore or HA evidence, no external penetration test, no Shariah UAT or parallel run, open sign-offs. The code-level P0/P1 findings are closed. Remaining code work: roadmap T-02 (rule pack versioning), signed daily close, pagination, GL export status, suspense.

"""
a = s.index("## 1. Architecture map")
s = s[:a] + section + s[a:]
s = s.replace("**NOT READY** for production, and **not yet a pilot candidate** for real customer money.",
              "**NOT READY** for production. (Before the fixes it was also not a pilot candidate; the code-level blockers are now closed. See section 0.)")
open(p, "w", encoding="utf-8").write(s)

# ---- UAT checklist: the new flows ---------------------------------------------------------------
p = "docs/UAT_CHECKLIST.md"
s = open(p, encoding="utf-8").read()
new_rows = """
## M. Added after the 2026-10-13 audit
| # | Step | Expected |
|---|---|---|
| M1 | Pool manager proposes a change to a reserve rate or cap (with a reason) | "Proposed"; nothing changes yet; the change appears in Governance Config |
| M2 | The same pool manager tries to approve it | Refused; a different finance checker approves, and only then the rate changes |
| M3 | Try to set a reserve balance through the screen or the API | Not possible; the balance only changes with signed runs |
| M4 | Risk proposes a change to a rule pack (WHT rates, Mudarib cap); then a finance checker or the authorized signatory approves | Rule pack unchanged until approved; both steps are in the audit trail |
| M5 | Prepare a distribution for an investment pool, submit; finance checker checks; Secretariat or Board reviews; signatory releases | Each step by a different person; the signatory cannot release before the review; a second release is refused |
| M6 | Leave a high-severity exception open on a pool, then try to release a run | Refused until the exception is decided |
| M7 | Open the Risk Limit screen | Limits show where they come from (rule pack or "placeholder defaults, not confirmed"); no regulator is named as the source |
| M8 | Sign in as the Super Admin and open the audit log | Who, what, when are visible; amounts and reasons are not |
| M9 | Try to change an account's opening date | Refused |
"""
a = s.index("## L. Sign-off")
s = s[:a] + new_rows.lstrip("\n") + "\n" + s[a:]
s = s.replace("Risk: everything except Administration. Signatory: Command Center, Products & Pools, Allocation, Investments,",
              "Risk: everything except Administration. Secretariat also sees Investments (the Shariah review of distributions). Signatory: Command Center, Products & Pools, Allocation, Investments,")
open(p, "w", encoding="utf-8").write(s)
print("done")
