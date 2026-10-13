import re

# ---- backend: expose the configured limits ------------------------------------------------------
p = "backend/apps/pools/concentration_engine.py"
s = open(p, encoding="utf-8").read()
old = '''        "limits_source": limits_source,
'''
new = '''        "limits_source": limits_source,
        "limits_pct": {key: float(value) for key, value in limits.items()},
'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)

# ---- frontend text and thresholds ---------------------------------------------------------------
p = "frontend/src/pages/RiskLimitDashboard.tsx"
s = open(p, encoding="utf-8").read()


def sub(old, new, count=1):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, count)


sub('useState("Commit secondary market syndication & asset re-allocation to ensure compliance within 90 days.")',
    'useState("")')
sub('Failed to submit SBP remediation plan.', 'Failed to record the remediation plan.')
sub('label: "SBP Single-Obligor Peak Exposure",\n        currentValue: Number(singleAssetConcentration.toFixed(1)),\n        thresholdValue: 15.0,',
    'label: "Single-Obligor Peak Exposure",\n        currentValue: Number(singleAssetConcentration.toFixed(1)),\n        thresholdValue: concentrationData?.limits_pct?.single_obligor_private ?? 15.0,')
sub('        ),\n        thresholdValue: 15.0,\n        unit: "%",\n        isLowerLimit: false,\n      },\n      {\n        label: "SBP Cash & Sovereign Buffer",',
    '        ),\n        thresholdValue: concentrationData?.limits_pct?.sector_real_estate ?? 15.0,\n        unit: "%",\n        isLowerLimit: false,\n      },\n      {\n        label: "SBP Cash & Sovereign Buffer",')
# drop the two gauges whose thresholds were invented (no configured source)
a = s.index('      {\n        label: "SBP Cash & Sovereign Buffer",')
b = s.index("    ]\n  }, [concentrationData, reservePolicies])")
s = s[:a] + s[b:]
sub("  }, [concentrationData, reservePolicies])", "  }, [concentrationData])")
sub("    const totalReserveBalances = reservePolicies.reduce((sum, r) => sum + Number(r.current_balance || 0), 0)\n    const reserveCushionPct = (totalReserveBalances / totalAssetValue) * 100\n", "")
sub("Calculating SBP Statutory Single-Obligor & Sector Concentration telemetry...", "Calculating concentration against the configured limits...")
sub('title="SBP Statutory Risk Limit & Concentration Cockpit"', 'title="Risk Limit & Concentration"')
sub('subtitle="SBP Prudential Regulations R-1 & R-6, Single Obligor caps, sector thresholds and automated breach remediation"',
    'subtitle="Exposure against the concentration limits configured in the jurisdiction rule pack, with a remediation worksheet for breaches"')
sub("{/* SBP Regulatory Alert Banner if any breaches exist */}", "{/* Alert banner if any configured limit is breached */}")
sub("SBP PR Regulatory Limit Alert: {breachesCount} Statutory Breaches Detected", "Concentration limit alert: {breachesCount} limit breach(es) detected")
sub("Certain obligor or sector exposures exceed SBP BPRD statutory limits (15% Single Obligor / 15% Real Estate). A formal remediation filing is required within 90 days.",
    "Some obligor or sector exposures are above the limits configured for this pool. Record how each one will be brought back within its limit; Risk & Compliance decides whether any regulatory notification applies.")
sub('label="Active SBP Breaches"', 'label="Active limit breaches"')
sub('"Requires ALCO filing"', '"Needs a decision"')
sub("Single Counterparty & Obligor Exposure Matrix (SBP Regulation R-1)", "Single Counterparty & Obligor Exposure Matrix")
s = re.sub(r"Statutory Limit: Maximum 15% of Pool Assets to any single private sector corporate obligor; 20% to connected groups; 25% to Sovereign-guaranteed public entities\.",
           "Limits come from the rule pack ({concentrationData?.limits_source ?? \"not loaded\"}).", s)
sub("File SBP Mitigation Plan &rarr;", "Record remediation plan &rarr;")
sub('title="Corporate Group Concentration (PR R-1)"', 'title="Corporate Group Concentration"')
sub("SBP PR Regulation R-1 caps total exposure to any connected corporate group or conglomerate at 20% of pool assets.",
    "Exposure to one connected group, against the group limit configured for this pool.")
sub('title="State Bank of Pakistan (SBP) Prudential Scorecard Matrix"', 'title="Limit Scorecard"')
sub("SBP Regulation Reference", "Measure")
sub("Statutory Description", "Description")
sub("Regulatory Cap", "Configured limit")
sub("Compliance Verdict", "Status")
sub("-20% SBP Baseline Stress", "-20% Moderate Stress")
sub("Statutory Cap</th>", "Configured limit</th>")
sub("Regulatory cases classified under SBP BPRD guidelines. Critical concentration breaches automatically prevent end-of-period profit distribution until ALCO sign-off.",
    "A high or critical exception that is still open stops the release of a profit run for the pool until it is decided.")
sub("SBP Statutory Concentration Breach Remediation", "Concentration Breach Remediation")
sub("has been logged in the Governance Queue. ALCO statutory filing memo prepared.", "has been logged in the Governance Queue. A remediation worksheet was prepared.")
sub("SBP BPRD Mandatory Remediation Strategy & ALCO Action Note:", "Remediation decision (what, who, by when):")
a = s.index('                  <div className="p-3 bg-navy-950 rounded border border-white/5 space-y-1.5 text-ink-muted">\n                    <div className="font-semibold text-ink-secondary">Mandatory Mitigation Steps:</div>')
b = s.index("                  </div>\n", s.index("File Form BPRD-PR1")) + len("                  </div>\n")
s = s[:a] + s[b:]
open(p, "w", encoding="utf-8").write(s)

# ---- frontend type ------------------------------------------------------------------------------
p = "frontend/src/api/concentrationRisk.ts"
s = open(p, encoding="utf-8").read()
old = "  breach_summary: {"
new = "  limits_source?: string\n  limits_pct?: Record<string, number>\n  breach_summary: {"
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
